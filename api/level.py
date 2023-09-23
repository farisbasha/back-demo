from django.utils import timezone
from django.db.models import Sum

from rest_framework import serializers,generics
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from apps.core.api.video import QuestionSerializer, VideoSerializer
from apps.core.models import Level, Question, Tutor, TutorLevelProgress, TutorVideoProgress, Video



#!Level ListCreateAPIView and RetrieveUpdateDestroyAPIView
class LevelSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Level
        fields = "__all__"
        

        
        
class LevelListCreateAPIView(generics.ListCreateAPIView):
    """
    This is used to get list of levels.
    """
    serializer_class = LevelSerializer
    queryset = Level.objects.all()
    
    def list(self, request, *args, **kwargs):
        levels = self.get_queryset()
        categorized_levels = {
            f'{Level.COURSE_TYPES.PART_TIME}': [],
            f'{Level.COURSE_TYPES.FULL_TIME}': []
        }

        for level in levels:
            categorized_levels[level.type].append(LevelSerializer(level).data)

        return Response(categorized_levels)

    
    
class LevelRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    This is used to get,update and delete level.
    """
    serializer_class = LevelSerializer
    queryset = Level.objects.all()
    

 
 
    
#!Level Order Arrangement API   

class LevelOrderSerializer(serializers.Serializer):
    levels = serializers.ListField(
        child=serializers.DictField(
            child=serializers.IntegerField(),
        )
    )
    
class LevelUpdateOrderAPIView(generics.UpdateAPIView):
    """
    API view to update the ordering of all levels.
    """
    serializer_class = LevelOrderSerializer
    queryset = Level.objects.all()

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        levels_list = serializer.validated_data['levels']

        # Update the order for each level in the list
        for level_data in levels_list:
            level_id = level_data['id']
            new_order = level_data['order']
            try:
                level = Level.objects.get(id=level_id)
                level.order = new_order
                level.save()
            except Level.DoesNotExist:
                # Handle the case if a level with the provided ID does not exist
                pass

        # Return success response
        return Response({'detail': 'Level ordering updated successfully.'}, status=status.HTTP_200_OK)
    
    


#! App API 


class BasicLevelDataAPIView(APIView):
    
    
    def get(self, request, *args, **kwargs):
       try:
            tutor = Tutor.objects.get(user=request.user)
            userType = tutor.user_type
            
            if userType:
                levels = Level.objects.filter(type=userType).order_by('order')
                level_data = []     
                isStartedAnyLevel = False

                
                for level in levels:
                    
                        
                    data = LevelSerializer(level).data
                    
                    data['no_of_videos'] = Video.objects.filter(level=level).count()
                    data['no_of_questions'] = Question.objects.filter(video__level=level).count()
                    completedVideos = TutorVideoProgress.objects.filter(tutor=tutor, video__level=level, status = TutorVideoProgress.STATUS_CHOICES.COMPLETED).order_by('video__order')
                    data['completed_videos'] = completedVideos.count()
                    
                    quizData = []
                    for cV in completedVideos:

                        if cV.quiz_percentage != 0:

                            quizData.append({
                                'video_id': cV.video.id,
                                'pass_percentage': cV.video.quiz_pass_percentage,
                                'actual_percentage': cV.quiz_percentage,
                                'video_title': cV.video.title,
                            })
                            
                    data['quiz_data'] = quizData
                    
                    levelProgress = TutorLevelProgress.objects.filter(tutor=tutor, level=level).first()
                    if not levelProgress:
                        levelProgress = TutorLevelProgress.objects.create(tutor=tutor, level=level)
                    
                    isStartedAnyLevel = isStartedAnyLevel or levelProgress.status == TutorLevelProgress.STATUS_CHOICES.STARTED or levelProgress.status == TutorLevelProgress.STATUS_CHOICES.EXPIRED

                    data['is_visible'] = levelProgress.is_visible
                    data['expiration_date'] = levelProgress.expiration_date
                    data['status'] = levelProgress.status
                    level_data.append(data)
                
                
                if not isStartedAnyLevel:
                    for level in level_data:
                        levelProgress = TutorLevelProgress.objects.filter(tutor=tutor, level=level['id']).first()
                        if levelProgress.status == TutorLevelProgress.STATUS_CHOICES.NOT_STARTED:
                            levelProgress.status = TutorLevelProgress.STATUS_CHOICES.STARTED
                            levelProgress.expiration_date = timezone.now() + timezone.timedelta(days=level['expire_duration_days'])
                            levelProgress.is_visible = True
                            levelProgress.save()
                            level['is_visible'] = levelProgress.is_visible
                            level['expiration_date'] = levelProgress.expiration_date
                            level['status'] = levelProgress.status

                            break 
                    # level_data[0]['is_visible'] = True
                    # level_data[0]['status'] = TutorLevelProgress.STATUS_CHOICES.STARTED
                    # levelP = TutorLevelProgress.objects.filter(tutor=tutor, level=levels[0]).first()
                    # levelP.is_visible = True
                    # levelP.status = TutorLevelProgress.STATUS_CHOICES.STARTED
                    # levelP.expiration_date = timezone.now() + timezone.timedelta(days=levels[0].expire_duration_days)
                    # level_data[0]['expiration_date'] = levelP.expiration_date
                    # levelP.save()
                    # firstVideo = Video.objects.filter(level=levels[0]).order_by('order').first()
                    # if  firstVideo:
                    #     TutorVideoProgress.objects.create(tutor=tutor, video=firstVideo)
                video_progress_agg = TutorVideoProgress.objects.filter(tutor=tutor, status=TutorVideoProgress.STATUS_CHOICES.COMPLETED).aggregate(Sum('current_time'))
                watchHours = round(video_progress_agg['current_time__sum'] / 3600, 2) if video_progress_agg['current_time__sum'] is not None else 0
                
                totalVideos = Video.objects.filter(level__type=tutor.user_type).count()
                completedVideos = TutorVideoProgress.objects.filter(tutor=tutor, status=TutorVideoProgress.STATUS_CHOICES.COMPLETED).count() 
                quizPerformanceData = TutorVideoProgress.objects.filter(tutor=tutor, status=TutorVideoProgress.STATUS_CHOICES.COMPLETED, quiz_percentage__gt=0).order_by('video__level__order','video__order').values_list('quiz_percentage', flat=True)
                print(quizPerformanceData)
                
                
                    
                return Response({'status': 'success', 'message': 'Levels and videos', 'data': {
                    'levels': level_data,
                    'watch_hours': watchHours,
                    'total_videos': totalVideos,
                    'completed_videos': completedVideos,
                    'quiz_performance': quizPerformanceData,
                    },}, status=status.HTTP_200_OK)
            else:
                return Response({'status': 'failed', 'message': 'User type not found', 'data': {}}, status=status.HTTP_404_NOT_FOUND)
       except Exception as e:
           print(e)
           return Response({'status': 'failed', 'message': 'An error occurred', 'data': {}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
        

# class StartLevelAPIView(APIView):
    
        
#         def post(self, request, *args, **kwargs):
#             try:
#                 level_id = request.data.get('level_id')
#                 tutor = Tutor.objects.get(user=request.user)
#                 level = Level.objects.get(id=level_id)
#                 #check already a TutorLevelProgress is in started or expired status
#                 levelProgress = TutorLevelProgress.objects.filter(tutor=tutor, level=level, status__in=['started', 'expired']).first()
#                 if levelProgress:
#                     return Response({'status': 'failed', 'message': 'A Level already started', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
        
#                 levelProgress = TutorLevelProgress.objects.filter(tutor=tutor, level=level,).first()
#                 if not levelProgress:
#                     levelProgress = TutorLevelProgress.objects.create(tutor=tutor, level=level)
#                 levelProgress.is_visible = True
#                 levelProgress.status = TutorLevelProgress.STATUS_CHOICES.STARTED
#                 levelProgress.save()
#                 return Response({'status': 'success', 'message': 'Level started', 'data': {}}, status=status.HTTP_200_OK)
#             except Level.DoesNotExist:
#                 return Response({'status': 'failed', 'message': 'Level not found', 'data': {}}, status=status.HTTP_404_NOT_FOUND)
#             except Exception as e:
#                 print(e)
#                 return Response({'status': 'failed', 'message': 'An error occurred', 'data': {}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class TutorLevelDetailAPIView(APIView):
    
    
    def get(self, request, *args, **kwargs):
        try:
            tutor = Tutor.objects.get(user=request.user)
            level_id = kwargs['level_id']
            level = Level.objects.get(id=level_id)
            isStartedAnyVideo = False
            # isAnyCurrentStartedVideoAvailable = False
            levelProgress = TutorLevelProgress.objects.filter(tutor=tutor, level=level).first()
            if not levelProgress:
                return Response({'status': 'failed', 'message': 'Level not started', 'data': {}}, status=status.HTTP_400_BAD_REQUEST)
            level_data = LevelSerializer(level).data
            level_data['videos']    = []
            videos = Video.objects.filter(level=level).order_by('order')
            for video in videos:
                video_data = VideoSerializer(video).data
                video_data['questions'] = []
                videoProgress = TutorVideoProgress.objects.filter(tutor=tutor, video=video).first()
                if not videoProgress:
                    videoProgress = TutorVideoProgress.objects.create(tutor=tutor, video=video)
                video_data['status'] = videoProgress.status
                video_data['current_time'] = videoProgress.current_time
                video_data['quiz_percentage'] = videoProgress.quiz_percentage
                isStartedAnyVideo = isStartedAnyVideo or videoProgress.status == TutorVideoProgress.STATUS_CHOICES.STARTED 
                # isAnyCurrentStartedVideoAvailable = isAnyCurrentStartedVideoAvailable or videoProgress.status == TutorVideoProgress.STATUS_CHOICES.STARTED
                questions = Question.objects.filter(video=video)
                for question in questions:
                    question_data = QuestionSerializer(question).data
                    video_data['questions'].append(question_data)
                level_data['videos'].append(video_data)
                
            if not isStartedAnyVideo:
                print("not started any video")
                for video in level_data['videos']:
                        videoProgress = TutorVideoProgress.objects.filter(tutor=tutor, video=video['id']).first()
                        if videoProgress.status == TutorVideoProgress.STATUS_CHOICES.NOT_STARTED:
                            videoProgress.status = TutorVideoProgress.STATUS_CHOICES.STARTED
                            videoProgress.save()
                            video['status'] = videoProgress.status
                         
                            break

            return Response({'status': 'success', 'message': 'Level details', 'data': level_data}, status=status.HTTP_200_OK)
        except Level.DoesNotExist:
            return Response({'status': 'failed', 'message': 'Level not found', 'data': {}}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e)
            return Response({'status': 'failed', 'message': 'An error occurred', 'data': {}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        





#? Dump codes

                # firstVideoProgress = TutorVideoProgress.objects.filter(tutor=tutor, video=level_data['videos'][0]['id']).
                # firstVideoProgress.status = TutorVideoProgress.STATUS_CHOICES.STARTED
                # firstVideoProgress.save()
                # level_data['videos'][0]['status'] = firstVideoProgress.status

            # if not isAnyCurrentStartedVideoAvailable and isStartedAnyVideo:
            #     print("isNoCurrentStartedVideo")
            #     for video in level_data['videos']:
            #             videoProgress = TutorVideoProgress.objects.filter(tutor=tutor, video=video['id']).first()
            #             if videoProgress.status == TutorVideoProgress.STATUS_CHOICES.NOT_STARTED:
            #                 videoProgress.status = TutorVideoProgress.STATUS_CHOICES.STARTED
            #                 videoProgress.save()
            #                 video['status'] = videoProgress.status
            #                 break

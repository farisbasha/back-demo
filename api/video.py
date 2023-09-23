from collections import defaultdict
from rest_framework import serializers,generics
from rest_framework.response import Response
from rest_framework import status
from apps.core.models import Level, Question, Tutor, TutorLevelProgress, TutorVideoProgress, Video

#!Question Serializer and CreateAPIView
class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'
        
class QuestionBulkCreateAPIView(generics.CreateAPIView):
    """
    This is used to create questions using video id.
    """
    serializer_class = QuestionSerializer
    queryset = Question.objects.all()
    
    def create(self, request, *args, **kwargs):
        video_id = kwargs['video_id']
        video = Video.objects.get(id=video_id)
        if not video:
            return Response({'detail': 'Video not found.'}, status=status.HTTP_404_NOT_FOUND)
        questions_data = request.data['questions']
        questions = []
        for question_data in questions_data:
            question_data['video'] = video
            question = Question(**question_data)
            question.save()
            questions.append(question)
        return Response(QuestionSerializer(questions, many=True).data, status=status.HTTP_201_CREATED)
    
class QuestionUpdateDeleteAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    This is used to delete question.
    """
    serializer_class = QuestionSerializer
    queryset = Question.objects.all()

#!Video ListCreateAPIView and RetrieveUpdateDestroyAPIView
class VideoListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ['id','title','order']
        
class VideoSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    
    class Meta:
        model = Video
        fields = "__all__"

        
class VideoListPIView(generics.ListAPIView):
    """
    This is used to get list of videos categorized by level and target user type.
    """
    serializer_class = VideoListSerializer

    def get_queryset(self):
        return Video.objects.all()

    def list(self, request, *args, **kwargs):
        videos = self.get_queryset().order_by('order')

        # Categorize videos based on level name and target user type
        categorized_videos = {
            f"{Level.COURSE_TYPES.PART_TIME}": [],
            f"{Level.COURSE_TYPES.FULL_TIME}": []
        }
        
        
            
        partime_level = Level.objects.filter(type=Level.COURSE_TYPES.PART_TIME).order_by('order')
        fulltime_level = Level.objects.filter(type=Level.COURSE_TYPES.FULL_TIME).order_by('order')
        
        for level in partime_level:
            level_name = level.name
            level_id = level.id
            level_order = level.order
            categorized_videos[f"{Level.COURSE_TYPES.PART_TIME}"].append({
                'id': level_id,
                'name': level_name,
                'order': level_order,
                'videos': VideoSerializer(videos.filter(level=level).order_by('order'),many=True).data,
            })
            
        for level in fulltime_level:
            level_name = level.name
            level_id = level.id
            level_order = level.order
            categorized_videos[f"{Level.COURSE_TYPES.FULL_TIME}"].append({
                'id': level_id,
                'name': level_name,
                'order': level_order,
                'videos': VideoSerializer(videos.filter(level=level).order_by('order'),many=True).data,
            })
        
        return Response(categorized_videos)
            


class VideoCreateAPIView(generics.CreateAPIView):
    """
    This is used to create video.
    """
    serializer_class = VideoSerializer
    queryset = Video.objects.all()

    def create(self, request, *args, **kwargs):
        questions_data = request.data.get('questions', [])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Save the video instance
        video = serializer.save()

        # Create and save question objects related to the video
        questions = []
        for question_data in questions_data:
            question_data['id'] = None
            question_data['video'] = video
            question = Question(**question_data)
            question.save()
            questions.append(question)

        response_data = {
            'video': VideoSerializer(video).data,
            'questions': QuestionSerializer(questions, many=True).data
        }
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    
class VideoRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    This is used to get,update and delete video.
    """
    serializer_class = VideoSerializer
    queryset = Video.objects.all()
    
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        questions_data = request.data.get('questions', [])

        # Clear existing questions associated with the video
        instance.questions.all().delete()

        # Update the video instance with the new data
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_video = serializer.save()

        # Create and save new question objects related to the video
        questions = []
        for question_data in questions_data:
            question_data['id'] = None
            question_data['video'] = updated_video
            question = Question(**question_data)
            question.save()
            questions.append(question)

        response_data = {
            'video': VideoSerializer(updated_video).data,
            'questions': QuestionSerializer(questions, many=True).data
        }
        return Response(response_data, status=status.HTTP_200_OK)
    

 
 
    
#!Video Order Arrangement API   


class VideoOrderSerializer(serializers.Serializer):
    videos = serializers.ListField(
        child=serializers.DictField(
            child=serializers.IntegerField(),
        )
    )

class VideoUpdateOrderAPIView(generics.UpdateAPIView):
    """
    API view to update the ordering of all videos.
    """
    serializer_class = VideoOrderSerializer
    queryset = Video.objects.all()

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        videos_list = serializer.validated_data['videos']

        # Update the order for each video in the list
        for video_data in videos_list:
            video_id = video_data['id']
            new_order = video_data['order']
            try:
                video = Video.objects.get(id=video_id)

                # Determine the target user type of the video
                video.order = new_order

                video.save()
            except Video.DoesNotExist:
                # Handle the case if a video with the provided ID does not exist
                pass

        # Return success response
        return Response({'detail': 'Video ordering updated successfully.'}, status=status.HTTP_200_OK)



class TutorVideoProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorVideoProgress
        fields = '__all__'


class UpdateTutorVideoProgressAPIView(generics.UpdateAPIView):
    """
    API view to update the progress of a tutor for a video.
    """
    serializer_class = TutorVideoProgressSerializer
    queryset = TutorVideoProgress.objects.all()

    def update(self, request, *args, **kwargs):
        video = Video.objects.get(id=kwargs['video_id'])
        tutor = Tutor.objects.get(user=request.user)
        try:
            tutor_video_progress = TutorVideoProgress.objects.get(video__id=video.id, tutor__id=tutor.id)
            serializer = self.get_serializer(tutor_video_progress, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            #if all video on this level is completed then update the level progress
            videos = Video.objects.filter(level=video.level)
            tutor_video_progresses = TutorVideoProgress.objects.filter(video__in=videos, tutor__id=tutor.id)
            if all([progress.status == TutorVideoProgress.STATUS_CHOICES.COMPLETED for progress in tutor_video_progresses]):
                tutor_level_progress = TutorLevelProgress.objects.get(level=video.level, tutor__id=tutor.id)
                tutor_level_progress.status = TutorLevelProgress.STATUS_CHOICES.COMPLETED
                tutor_level_progress.save()
            
                return Response({
                    'detail': 'Tutor video progress updated successfully.',
                    'is_level_completed': True
                    }, status=status.HTTP_200_OK)
            
            return Response({'detail': 'Tutor video progress updated successfully.','is_level_completed': False}, status=status.HTTP_200_OK)
        except TutorVideoProgress.DoesNotExist:
            return Response({'detail': 'Tutor video progress not found.'}, status=status.HTTP_404_NOT_FOUND)


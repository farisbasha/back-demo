import calendar
from rest_framework import generics, serializers
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Avg,Sum
from django.db.models.functions import TruncMonth

from apps.core.models import Level, Tutor, TutorLevelProgress, TutorVideoProgress, Video


class AdminHomeReportAPI(APIView):
    def get(self, request):
        try:
            parttimeTutorCount = Tutor.objects.filter(
                user_type=Tutor.USER_TYPES.PART_TIME
            ).count()
            fulltimeTutorCount = Tutor.objects.filter(
                user_type=Tutor.USER_TYPES.FULL_TIME
            ).count()

            parttimeLevelCount = Level.objects.filter(
                type=Level.COURSE_TYPES.PART_TIME
            ).count()
            fulltimeLevelCount = Level.objects.filter(
                type=Level.COURSE_TYPES.FULL_TIME
            ).count()

            parttimeVideoCount = Video.objects.filter(
                level__type=Level.COURSE_TYPES.PART_TIME
            ).count()
            fulltimeVideoCount = Video.objects.filter(
                level__type=Level.COURSE_TYPES.FULL_TIME
            ).count()

            tutors = Tutor.objects.all().order_by("-user__date_joined")

            lastJoinedTutorsData = []
            for tutor in tutors[:10]:
                lastJoinedTutorsData.append(
                    {
                        "name": tutor.name,
                        "email": tutor.email,
                        "user_type": tutor.user_type,
                        "date_joined": tutor.user.date_joined,
                    }
                )

            parttimeTutorCounts = (
                Tutor.objects.filter(user_type=Tutor.USER_TYPES.PART_TIME)
                .annotate(month=TruncMonth("user__date_joined"))
                .values("month")
                .annotate(count=Count("id"))
            )

            # Calculate full-time tutor counts by month
            fulltimeTutorCounts = (
                Tutor.objects.filter(user_type=Tutor.USER_TYPES.FULL_TIME)
                .annotate(month=TruncMonth("user__date_joined"))
                .values("month")
                .annotate(count=Count("id"))
            )

            # Create a list of all unique months
            all_months = set(
                [
                    calendar.month_name[month["month"].month]
                    for month in parttimeTutorCounts
                ]
                + [
                    calendar.month_name[month["month"].month]
                    for month in fulltimeTutorCounts
                ]
            )

            # Create dictionaries to hold counts for each user type
            parttime_counts_dict = {month: 0 for month in all_months}
            fulltime_counts_dict = {month: 0 for month in all_months}

            # Populate the part-time counts dictionary with actual counts
            for parttime_count in parttimeTutorCounts:
                month_name = calendar.month_name[parttime_count["month"].month]
                parttime_counts_dict[month_name] = parttime_count["count"]

            # Populate the full-time counts dictionary with actual counts
            for fulltime_count in fulltimeTutorCounts:
                month_name = calendar.month_name[fulltime_count["month"].month]
                fulltime_counts_dict[month_name] = fulltime_count["count"]

            # Create series data for part-time tutors
            parttimeSeries = {
                "name": "Part-Time Tutors",
                "data": [parttime_counts_dict[month] for month in all_months],
            }

            # Create series data for full-time tutors
            fulltimeSeries = {
                "name": "Full-Time Tutors",
                "data": [fulltime_counts_dict[month] for month in all_months],
            }

            parttimeGraphData = parttimeSeries
            fulltimeGraphData = fulltimeSeries

            data = {
                "parttimeTutorCount": parttimeTutorCount,
                "fulltimeTutorCount": fulltimeTutorCount,
                "parttimeLevelCount": parttimeLevelCount,
                "fulltimeLevelCount": fulltimeLevelCount,
                "parttimeVideoCount": parttimeVideoCount,
                "fulltimeVideoCount": fulltimeVideoCount,
                "lastJoinedTutors": lastJoinedTutorsData,
                "parttimeGraphData": parttimeGraphData,
                "fulltimeGraphData": fulltimeGraphData,
                "categories": list(all_months),
            }
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(
                {"error": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReportGraphDataAPIView(APIView):
    def get(self, request, type):
        try:
            levelProgressList = TutorLevelProgress.objects.filter(tutor__user_type=type)
            levels = Level.objects.filter(type=type)
            totalTutorCount = Tutor.objects.filter(user_type=type).count()
            levelStatusData = []
            quizAvgEachLevel = []
            levelCompletionPercentage = []
            for level in levels:
                levelStatusData.append(
                    {
                        "name": level.name,
                        "completed": levelProgressList.filter(
                            level=level,
                            status=TutorLevelProgress.STATUS_CHOICES.COMPLETED,
                        ).count(),
                        "expired": levelProgressList.filter(
                            level=level,
                            status=TutorLevelProgress.STATUS_CHOICES.EXPIRED,
                        ).count(),
                        "started": levelProgressList.filter(
                            level=level,
                            status=TutorLevelProgress.STATUS_CHOICES.STARTED,
                        ).count(),
                        "not_started": levelProgressList.filter(
                            level=level,
                            status=TutorLevelProgress.STATUS_CHOICES.NOT_STARTED,
                        ).count(),
                    }
                )
                avgQuiz = (
                    TutorVideoProgress.objects.filter(
                        video__level=level, quiz_percentage__gt=0
                    ).aggregate(Avg("quiz_percentage"))["quiz_percentage__avg"]
                    or 0
                )
                quizAvgEachLevel.append({"name": level.name, "avg": round(avgQuiz, 2)})
                levelCompletionPercentage.append(
                    {
                        "name": level.name,
                        "percentage": round(
                            (
                                levelProgressList.filter(
                                    level=level,
                                    status=TutorLevelProgress.STATUS_CHOICES.COMPLETED,
                                ).count()
                                / totalTutorCount
                            )
                            * 100,
                            2,
                        ),
                    }
                )

            data = {
                "levelStatusData": levelStatusData,
                "quizAvgEachLevel": quizAvgEachLevel,
                "levelCompletionPercentage": levelCompletionPercentage,
            }
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(
                {"error": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReportLevelAndVideoFilterListAPIView(APIView):
    def get(self, request, type):
        try:
            levels = Level.objects.filter(type=type)
            levelData = []
            for level in levels:
                data = {
                    "value": level.id,
                    "label": level.name,
                }
                videoData = []
                videos = Video.objects.filter(level=level)
                for video in videos:
                    videoData.append(
                        {
                            "value": video.id,
                            "label": video.title,
                        }
                    )
                data["videos"] = videoData
                levelData.append(data)

            data = {
                "levelData": levelData,
                "levelStatus": [
                    {"value": status[0], "label": status[1]}
                    for status in TutorLevelProgress.STATUS_CHOICES.choices
                ],
                "videoStatus": [
                    {"value": status[0], "label": status[1]}
                    for status in TutorVideoProgress.STATUS_CHOICES.choices
                ],
            }
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(
                {"error": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReportFilterSerializer(serializers.Serializer):
    level = serializers.IntegerField(required=True)
    level_status = serializers.ChoiceField(
        choices=TutorLevelProgress.STATUS_CHOICES, required=True
    )
    video = serializers.IntegerField(required=False)
    video_status = serializers.ChoiceField(
        choices=TutorVideoProgress.STATUS_CHOICES, required=False
    )
    type = serializers.ChoiceField(choices=Tutor.USER_TYPES, required=True)


class ReportFilterAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ReportFilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        level = serializer.validated_data.get("level")
        level_status = serializer.validated_data.get("level_status")
        video = serializer.validated_data.get("video")
        video_status = serializer.validated_data.get("video_status")
        type = serializer.validated_data.get("type")

        # Filter tutors based on level and level status
        tutors = Tutor.objects.filter(user_type=type)
        if level:
            tutors = tutors.filter(tutorlevelprogress__level__id=level)
            if level_status:
                tutors = tutors.filter(
                    tutorlevelprogress__level__id=level,
                    tutorlevelprogress__status=level_status,
                )
            # Filter tutors based on video and video status
            if video:
                tutors = tutors.filter(tutorvideoprogress__video__id=video)
                if video_status:
                    tutors = tutors.filter(
                        tutorvideoprogress__video__id=video,
                        tutorvideoprogress__status=video_status,
                    )
            elif video_status:
                tutors = tutors.filter(
                    tutorvideoprogress__status=video_status,
                )

        tutors = tutors.distinct()
        tutor_data =[]
        for tutor in tutors:
            data = {
                "id": tutor.id,
                "name": tutor.name,
                "email": tutor.email,
                # Add more fields as needed
            }
            current_level = TutorLevelProgress.objects.filter(tutor=tutor, status__in=[TutorLevelProgress.STATUS_CHOICES.STARTED,TutorLevelProgress.STATUS_CHOICES.EXPIRED]).first()
            data['currentLevel'] = current_level.level.name if current_level else "N/A"
            video_progress_agg = TutorVideoProgress.objects.filter(tutor=tutor, status=TutorVideoProgress.STATUS_CHOICES.COMPLETED).aggregate(Sum('current_time'))
            data['watchHours'] = round(video_progress_agg['current_time__sum'] / 3600, 2) if video_progress_agg['current_time__sum'] is not None else 0

            tutor_data.append(data)

        return Response(tutor_data, status=status.HTTP_200_OK)

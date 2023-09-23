from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status,generics,serializers
import requests
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from django.conf import settings
from django.db.models import Sum,Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from apps.core.models import Level, Tutor, TutorLevelProgress, TutorVideoProgress
from models import CustomUser  # Import your Tutor model here
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny

class TutorLoginAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')

        try:
            tutor = Tutor.objects.get(email=email)
            if not check_password(password, tutor.user.password):
                return Response({'status': 'failed', 'message': 'Invalid Credential', 'data': {}}, status=status.HTTP_401_UNAUTHORIZED)

            # Log in the tutor and generate a token
            user = tutor.user
            token, created = Token.objects.get_or_create(user=user)

            tutor_data = {
                'id': tutor.id,
                'ref_id': tutor.ref_id,
                'name': tutor.name,
                'email': tutor.email,
                'user_type': tutor.user_type,
                'token': token.key  # Include the token in the response
            }
            return Response({'status': 'success', 'message': 'Tutor already exists', 'data': tutor_data}, status=status.HTTP_200_OK)
        except Tutor.DoesNotExist:
            api_url = 'http://165.232.189.28:5000/apis/employeeLogin'  # Replace with the actual URL
            api_data = {'email': email, 'password': password}
            headers = {'Authorization': f'Bearer {settings.LOGIN_TOKEN}'}

            try:
                response = requests.get(api_url, json=api_data, timeout=10, headers=headers)  # Set an appropriate timeout value
                response_data = response.json()

                if response_data.get('status') == 'success':
                    # Create a new CustomUser object with password
                    user = CustomUser.objects.create(
                        email=response_data['data']['email'],
                        first_name=response_data['data']['name'],
                        password=make_password(password),  # Hash the password before saving
                        is_active=True
                    )
                    user.save()

                    tutor = Tutor.objects.create(
                        ref_id=response_data['data']['id'],
                        name=response_data['data']['name'],
                        email=response_data['data']['email'],
                        user_type=response_data['data']['userType'],
                        user=user
                    )

                    # Log in the tutor and generate a token
                    token, created = Token.objects.get_or_create(user=user)

                    tutor_data = {
                        'id': tutor.id,
                        'ref_id': tutor.ref_id,
                        'name': tutor.name,
                        'email': tutor.email,
                        'user_type': tutor.user_type,
                        'token': token.key  # Include the token in the response
                    }
                    return Response({'status': 'success', 'message': 'Tutor logged in and stored in the database', 'data': tutor_data}, status=status.HTTP_200_OK)
                else:
                    return Response({'status': 'failed', 'message': 'User not found', 'data': {}}, status=status.HTTP_404_NOT_FOUND)
            except requests.exceptions.Timeout:
                return Response({'status': 'failed', 'message': 'API timeout', 'data': {}}, status=status.HTTP_504_GATEWAY_TIMEOUT)
            except Exception as e:
                return Response({'status': 'failed', 'message': 'An error occurred', 'data': {}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




#Profile getting with token
class TutorProfileView(APIView):
    
    
    def get(self, request, *args, **kwargs):
        token = request.headers.get('Authorization').split(' ')[1]
        try:
            tutor = Tutor.objects.get(user__auth_token__key=token)
            tutor_data = {
                'id': tutor.id,
                'ref_id': tutor.ref_id,
                'name': tutor.name,
                'email': tutor.email,
                'user_type': tutor.user_type,
                'token': token  # Include the token in the response
            }
            return Response({'status': 'success', 'message': 'Tutor profile', 'data': tutor_data}, status=status.HTTP_200_OK)
        except Tutor.DoesNotExist:
            return Response({'status': 'failed', 'message': 'Tutor not found', 'data': {}}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'status': 'failed', 'message': 'An error occurred', 'data': {}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework import serializers

class TutorListSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Tutor
        fields = ['id', 'ref_id', 'name', 'email', 'user_type', 'progress']

    def get_progress(self, tutor):
        progress_data = {}


        # progress_data['completed_level'] = [level.level.name for level in completed_levels]
        progress_data['completed_level'] = TutorLevelProgress.objects.filter(tutor=tutor, status=TutorLevelProgress.STATUS_CHOICES.COMPLETED).count()


       
        current_level = TutorLevelProgress.objects.filter(tutor=tutor, status__in=[TutorLevelProgress.STATUS_CHOICES.STARTED,TutorLevelProgress.STATUS_CHOICES.EXPIRED]).first()
        if current_level:
            progress_data['current_completed_videos_count'] = TutorVideoProgress.objects.filter(tutor=tutor, video__level=current_level.level, status=TutorVideoProgress.STATUS_CHOICES.COMPLETED).count()
            progress_data['current_level_visible'] = current_level.is_visible
            progress_data['current_level_status'] = current_level.status
            progress_data['current_level'] = current_level.level.name 
        else:
            progress_data['current_completed_videos_count'] = 0
            progress_data['current_level_visible'] = False
            progress_data['current_level_status'] = TutorLevelProgress.STATUS_CHOICES.NOT_STARTED
            progress_data['current_level'] = None

        video_progress_agg = TutorVideoProgress.objects.filter(tutor=tutor, status=TutorVideoProgress.STATUS_CHOICES.COMPLETED).aggregate(Sum('current_time'))
        progress_data['watch_hour'] = round(video_progress_agg['current_time__sum'] / 3600, 2) if video_progress_agg['current_time__sum'] is not None else 0

        video_progress_agg = TutorVideoProgress.objects.filter(tutor=tutor, status=TutorVideoProgress.STATUS_CHOICES.COMPLETED).aggregate(Count('id'))
        progress_data['total_video_completed_count'] = video_progress_agg['id__count']

        return progress_data


class TutorListAPIView(generics.ListAPIView):
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter,filters.OrderingFilter]
    filterset_fields = ['user_type',]  # Add the fields you want to use for filtering
    search_fields = ['name', 'email']  # Add the fields you want to use for searching
    ordering_fields = ['name', 'email','user_type', ]  # Add the fields you want to use for ordering
    serializer_class = TutorListSerializer
    queryset = Tutor.objects.all()
    
    
   
class TutorCurrentLevelToggleAPIView(APIView):
    def post(self, request, format=None):
        data = request.data
        try:
            tutor_id = data['tutor_id']
            tutor_obj = Tutor.objects.get(id=tutor_id)
            current_level = TutorLevelProgress.objects.filter(tutor=tutor_obj, status__in=[TutorLevelProgress.STATUS_CHOICES.STARTED,TutorLevelProgress.STATUS_CHOICES.EXPIRED]).first()
            if current_level:
                current_level.is_visible = not current_level.is_visible
                current_level.save()
                return Response({'message': 'Level Visibility Updated'}, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'No Level Found'}, status=status.HTTP_404_NOT_FOUND)
        except:
            return Response({'message': 'Tutor Not Found or no enough data'}, status=status.HTTP_404_NOT_FOUND)
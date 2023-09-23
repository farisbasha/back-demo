from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status,generics,serializers
from django.utils import timezone



from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from apps.core.models import Level, RenewalRequest, Tutor, TutorLevelProgress

from rest_framework import serializers


from models import CustomUser

class RenewalRequestSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = RenewalRequest
        fields = '__all__'
        depth = 1


class RenewalRequestListAPIView(generics.ListAPIView):
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter,filters.OrderingFilter]
    filterset_fields = ['tutor__user_type','is_accepted']  # Add the fields you want to use for filtering
    search_fields = ['tutor__name', 'tutor__email']  # Add the fields you want to use for searching
    ordering_fields = ['request_date','tutor__name', 'tutor__email','tutor__user_type', ]  # Add the fields you want to use for ordering
    serializer_class = RenewalRequestSerializer
    queryset = RenewalRequest.objects.all()
    
    
    
class RenewalAcceptAPIView(APIView):
    def post(self, request, format=None):
        data = request.data
        try:
            renewal_id = data['renewal_id']
            renewal_obj = RenewalRequest.objects.get(id=renewal_id)
            days = data['days']
            level_progress = TutorLevelProgress.objects.get(tutor=renewal_obj.tutor, level=renewal_obj.level)
            level_progress.status = TutorLevelProgress.STATUS_CHOICES.STARTED
            level_progress.expiration_date = timezone.now() + timezone.timedelta(days=days)
            level_progress.save()
            renewal_obj.is_accepted = True
            renewal_obj.save()
            ctx ={
                    'title': 'Renewal Accepted',
                    'body': f"Your renewal request for {renewal_obj.level.name} has been accepted. You can now access the level for {days} days."
                }
            
            return Response({'message': 'Renewal Accepted'}, status=status.HTTP_200_OK)
        except:
            return Response({'message': 'Renewal Not Found or Days not provided'}, status=status.HTTP_404_NOT_FOUND)
   
   
class RenewalRequestCreateAPIView(APIView):
    def post(self, request, format=None):
        data = request.data
        try:

            level_id = data['level_id']
            tutor_obj = Tutor.objects.get(user=request.user)
            level_obj = Level.objects.get(id=level_id)
            if RenewalRequest.objects.filter(tutor=tutor_obj, level=level_obj, is_accepted=False).exists():
                return Response({'message': 'Renewal Already Requested'}, status=status.HTTP_400_BAD_REQUEST)
            levelProgress = TutorLevelProgress.objects.filter(tutor=tutor_obj, level=level_obj).first()
            renewal_obj = RenewalRequest.objects.create(tutor=tutor_obj, level=level_obj,expired_date=levelProgress.expiration_date)
            
            
            return Response({'message': 'Renewal Request Created'}, status=status.HTTP_200_OK)
        except:
            return Response({'message': 'Tutor or Level Not Found'}, status=status.HTTP_404_NOT_FOUND)
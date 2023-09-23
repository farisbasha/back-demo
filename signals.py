from django.db.models.signals import post_save,pre_save,post_delete
from django.dispatch import receiver

from apps.core.models import Level, RenewalRequest, SendNotification, Video

from apps.core.utils.link_convert import convert_share_link_to_downloadable
from .models import CustomUser





#! Level Signals

@receiver(pre_save, sender=Level)
def level_pre_save(sender, instance:Level, **kwargs):
    if instance.id is None:
        # Get the last Level object based on the order field in descending order
        last_level = Level.objects.filter(type=instance.type).order_by('-order').first()

        if last_level:
            # If there are existing levels, set the new level order to be one greater than the last level's order
            instance.order = last_level.order + 1
        else:
            # If no levels exist, set the new level order to be 1
            instance.order = 0
            
@receiver(post_delete, sender=Level)
def level_post_delete(sender, instance: Level, **kwargs):
    # Get all levels with an order greater than the deleted level's order
    levels_to_update = Level.objects.filter(type=instance.type, order__gt=instance.order)

    # Decrease the order of each level in the queryset
    for level in levels_to_update:
        level.order -= 1
        level.save()
        

#! Video Signals

@receiver(pre_save, sender=Video)
def video_pre_save(sender, instance: Video, **kwargs):
    if instance.id is None:
        # Get the last Video object based on the order field in descending order
        last_video = Video.objects.filter(level=instance.level).order_by('-order').first()

        if last_video:
            # If there are existing videos with the same level and target, set the new video order to be one greater than the last video's order
            instance.order = last_video.order + 1
        else:
            # If no videos exist for the same level and target, set the new video order to be 1
            instance.order = 0
            
        instance.video_link_low = convert_share_link_to_downloadable(instance.video_link_low)
        instance.video_link_high = convert_share_link_to_downloadable(instance.video_link_high)
        instance.thumbnail_image = convert_share_link_to_downloadable(instance.thumbnail_image)
        
    else:
        existing_video = Video.objects.get(pk=instance.id)

        # Check if the video links have been updated and are different from the existing links
        if existing_video.video_link_low != instance.video_link_low:
            instance.video_link_low = convert_share_link_to_downloadable(instance.video_link_low)

        if existing_video.video_link_high != instance.video_link_high:
            instance.video_link_high = convert_share_link_to_downloadable(instance.video_link_high)

        if existing_video.thumbnail_image != instance.thumbnail_image:
            instance.thumbnail_image = convert_share_link_to_downloadable(instance.thumbnail_image)
            
@receiver(post_delete, sender=Video)
def video_post_delete(sender, instance: Video, **kwargs):
    # Get all videos with the same level, target, and an order greater than the deleted video's order
    videos_to_update = Video.objects.filter(level=instance.level, order__gt=instance.order)

    # Decrease the order of each video in the queryset
    for video in videos_to_update:
        video.order -= 1
        video.save()
        
   
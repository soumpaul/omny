from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import Device, DeviceAlert, EmergencyEvent, Space, SOSButtonConfiguration
from .serializers import (
    DeviceSerializer,
    DeviceRegistrationSerializer,
    DeviceAlertSerializer,
    DeviceAlertCreateSerializer,
    EmergencyEventSerializer,
    EmergencyEventCreateSerializer,
    SpaceSerializer,
    SOSButtonConfigurationSerializer,
)

User = get_user_model()


class DeviceRegistrationView(APIView):
    """
    Register a new device
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Devices'],
        summary='Register a new device',
        description='Register a new device (watch or SOS button) for a user or space',
        request=DeviceRegistrationSerializer,
        responses={201: DeviceSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = DeviceRegistrationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        device_id = data.get('device_id')
        
        # Check if device already exists
        if Device.objects.filter(device_id=device_id).exists():
            return Response(
                {'error': 'Device with this device_id already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify user has access to the household
        user_id = data.get('user_id')
        space_id = data.get('space_id')
        
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                # Verify requesting user is in same household
                if request.user.household != user.household:
                    return Response(
                        {'error': 'You do not have permission to register devices for this user'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        if space_id:
            try:
                space = Space.objects.get(id=space_id)
                # Verify requesting user is in same household
                if request.user.household != space.household:
                    return Response(
                        {'error': 'You do not have permission to register devices for this space'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Space.DoesNotExist:
                return Response(
                    {'error': 'Space not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Create device
        try:
            with transaction.atomic():
                device = Device.objects.create(
                    device_id=device_id,
                    device_type=data.get('device_type'),
                    name=data.get('name'),
                    manufacturer=data.get('manufacturer', ''),
                    model=data.get('model', ''),
                    serial_number=data.get('serial_number', ''),
                    firmware_version=data.get('firmware_version', ''),
                    user_id=user_id,
                    space_id=space_id,
                    installed_date=data.get('installed_date'),
                    notes=data.get('notes', ''),
                    status='active',
                    last_online=timezone.now(),
                )
                
                serializer = DeviceSerializer(device)
                return Response({
                    'message': 'Device registered successfully',
                    'device': serializer.data
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response(
                {'error': f'Failed to register device: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeviceListView(APIView):
    """
    List all devices for the user's household
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Devices'],
        summary='List devices',
        description='List all devices in the authenticated user\'s household',
        responses={200: DeviceSerializer(many=True)}
    )
    def get(self, request):
        if not request.user.household:
            return Response(
                {'error': 'User is not associated with a household'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all devices in the household
        devices = Device.objects.filter(
            user__household=request.user.household
        ) | Device.objects.filter(
            space__household=request.user.household
        )
        
        devices = devices.distinct().order_by('-created_at')
        
        serializer = DeviceSerializer(devices, many=True)
        return Response({
            'devices': serializer.data,
            'count': devices.count()
        }, status=status.HTTP_200_OK)


class DeviceDetailView(APIView):
    """
    Get, update, or delete a specific device
    """
    permission_classes = [IsAuthenticated]
    
    def get_device(self, device_id, user):
        """Get device and verify user has access"""
        try:
            device = Device.objects.get(device_id=device_id)
            household = device.get_household()
            
            if household != user.household:
                return None, Response(
                    {'error': 'You do not have permission to access this device'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return device, None
            
        except Device.DoesNotExist:
            return None, Response(
                {'error': 'Device not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        tags=['Devices'],
        summary='Get device details',
        description='Get details of a specific device by device_id',
        responses={200: DeviceSerializer, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
    def get(self, request, device_id):
        device, error_response = self.get_device(device_id, request.user)
        if error_response:
            return error_response
        
        serializer = DeviceSerializer(device)
        return Response({'device': serializer.data}, status=status.HTTP_200_OK)
    
    @extend_schema(
        tags=['Devices'],
        summary='Update device',
        description='Update device fields (name, status, battery_level, etc.)',
        request=OpenApiTypes.OBJECT,
        responses={200: DeviceSerializer, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
    def patch(self, request, device_id):
        device, error_response = self.get_device(device_id, request.user)
        if error_response:
            return error_response
        
        # Update allowed fields
        allowed_fields = [
            'name', 'status', 'battery_level', 'last_online',
            'firmware_version', 'notes', 'manufacturer', 'model'
        ]
        
        for field in allowed_fields:
            if field in request.data:
                setattr(device, field, request.data[field])
        
        try:
            device.save()
            serializer = DeviceSerializer(device)
            return Response({
                'message': 'Device updated successfully',
                'device': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f'Failed to update device: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        tags=['Devices'],
        summary='Delete device',
        description='Delete a device from the system',
        responses={200: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
    def delete(self, request, device_id):
        device, error_response = self.get_device(device_id, request.user)
        if error_response:
            return error_response
        
        try:
            device.delete()
            return Response(
                {'message': 'Device deleted successfully'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to delete device: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeviceAlertCreateView(APIView):
    """
    Create a device alert (low battery, offline, etc.)
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Alerts'],
        summary='Create device alert',
        description='Create a device alert for low battery, offline status, or maintenance',
        request=DeviceAlertCreateSerializer,
        responses={201: DeviceAlertSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = DeviceAlertCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        device_id = data.get('device_id')
        
        try:
            device = Device.objects.get(device_id=device_id)
            
            # Verify user has access to this device's household
            household = device.get_household()
            if household != request.user.household:
                return Response(
                    {'error': 'You do not have permission to create alerts for this device'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Create alert
            alert = DeviceAlert.objects.create(
                device=device,
                alert_type=data.get('alert_type'),
                severity=data.get('severity'),
                message=data.get('message'),
                metadata=data.get('metadata'),
            )
            
            serializer = DeviceAlertSerializer(alert)
            return Response({
                'message': 'Alert created successfully',
                'alert': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Device.DoesNotExist:
            return Response(
                {'error': 'Device not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to create alert: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeviceAlertListView(APIView):
    """
    List device alerts for the user's household
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Alerts'],
        summary='List device alerts',
        description='List all device alerts for the household with optional filters',
        parameters=[
            OpenApiParameter('device_id', str, description='Filter by device ID'),
            OpenApiParameter('is_acknowledged', bool, description='Filter by acknowledgment status'),
            OpenApiParameter('severity', str, description='Filter by severity level')
        ],
        responses={200: DeviceAlertSerializer(many=True)}
    )
    def get(self, request):
        if not request.user.household:
            return Response(
                {'error': 'User is not associated with a household'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all alerts for devices in the household
        alerts = DeviceAlert.objects.filter(
            device__user__household=request.user.household
        ) | DeviceAlert.objects.filter(
            device__space__household=request.user.household
        )
        
        alerts = alerts.distinct()
        
        # Apply filters
        device_id = request.query_params.get('device_id')
        if device_id:
            alerts = alerts.filter(device__device_id=device_id)
        
        is_acknowledged = request.query_params.get('is_acknowledged')
        if is_acknowledged is not None:
            alerts = alerts.filter(is_acknowledged=is_acknowledged.lower() == 'true')
        
        severity = request.query_params.get('severity')
        if severity:
            alerts = alerts.filter(severity=severity)
        
        alerts = alerts.order_by('-created_at')
        
        serializer = DeviceAlertSerializer(alerts, many=True)
        return Response({
            'alerts': serializer.data,
            'count': alerts.count()
        }, status=status.HTTP_200_OK)


class DeviceAlertAcknowledgeView(APIView):
    """
    Acknowledge a device alert
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Alerts'],
        summary='Acknowledge alert',
        description='Mark a device alert as acknowledged',
        request=None,
        responses={200: DeviceAlertSerializer, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
    def post(self, request, alert_id):
        try:
            alert = DeviceAlert.objects.get(id=alert_id)
            
            # Verify user has access
            household = alert.device.get_household()
            if household != request.user.household:
                return Response(
                    {'error': 'You do not have permission to acknowledge this alert'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Acknowledge alert
            alert.is_acknowledged = True
            alert.acknowledged_by = request.user
            alert.acknowledged_at = timezone.now()
            alert.save()
            
            serializer = DeviceAlertSerializer(alert)
            return Response({
                'message': 'Alert acknowledged successfully',
                'alert': serializer.data
            }, status=status.HTTP_200_OK)
            
        except DeviceAlert.DoesNotExist:
            return Response(
                {'error': 'Alert not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to acknowledge alert: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmergencyEventCreateView(APIView):
    """
    Create an emergency event (fall detection, SOS button press)
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Emergencies'],
        summary='Create emergency event',
        description='Create an emergency event for fall detection or SOS button press',
        request=EmergencyEventCreateSerializer,
        responses={201: EmergencyEventSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = EmergencyEventCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        device_id = data.get('device_id')
        
        try:
            device = Device.objects.get(device_id=device_id)
            
            # Verify user has access to this device's household
            household = device.get_household()
            if household != request.user.household:
                return Response(
                    {'error': 'You do not have permission to create emergencies for this device'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get SOS configuration if this is an SOS event
            sos_config = None
            event_type = data.get('event_type')
            if event_type.startswith('sos_'):
                tap_count = data.get('tap_count')
                try:
                    sos_config = SOSButtonConfiguration.objects.get(
                        device=device,
                        tap_count=tap_count,
                        is_active=True
                    )
                except SOSButtonConfiguration.DoesNotExist:
                    pass
            
            # Create emergency event
            with transaction.atomic():
                emergency = EmergencyEvent.objects.create(
                    device=device,
                    event_type=event_type,
                    severity=data.get('severity'),
                    message=data.get('message'),
                    location_data=data.get('location_data'),
                    sensor_data=data.get('sensor_data'),
                    sos_configuration=sos_config,
                    notification_status='pending',
                )
                
                # Get all caregivers in the household to notify
                caregivers = household.members.filter(
                    household_role__in=['primary_caregiver', 'caregiver']
                )
                
                # If SOS config exists, use its specific caregiver list
                if sos_config:
                    caregivers = sos_config.notify_caregivers.all()
                
                # Add caregivers to notification list
                emergency.notified_caregivers.set(caregivers)
                emergency.notification_status = 'sent'
                emergency.save()
                
                # TODO: Implement actual notification sending (push, SMS, call)
                # This would integrate with Firebase Cloud Messaging, Twilio, etc.
                
                serializer = EmergencyEventSerializer(emergency)
                return Response({
                    'message': 'Emergency event created successfully',
                    'emergency': serializer.data,
                    'notified_caregivers_count': caregivers.count()
                }, status=status.HTTP_201_CREATED)
            
        except Device.DoesNotExist:
            return Response(
                {'error': 'Device not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to create emergency event: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmergencyEventListView(APIView):
    """
    List emergency events for the user's household
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Emergencies'],
        summary='List emergency events',
        description='List all emergency events for the household with optional filters',
        parameters=[
            OpenApiParameter('device_id', str, description='Filter by device ID'),
            OpenApiParameter('event_type', str, description='Filter by event type'),
            OpenApiParameter('responded', bool, description='Filter by response status')
        ],
        responses={200: EmergencyEventSerializer(many=True)}
    )
    def get(self, request):
        if not request.user.household:
            return Response(
                {'error': 'User is not associated with a household'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all emergencies for devices in the household
        emergencies = EmergencyEvent.objects.filter(
            device__user__household=request.user.household
        ) | EmergencyEvent.objects.filter(
            device__space__household=request.user.household
        )
        
        emergencies = emergencies.distinct()
        
        # Apply filters
        device_id = request.query_params.get('device_id')
        if device_id:
            emergencies = emergencies.filter(device__device_id=device_id)
        
        event_type = request.query_params.get('event_type')
        if event_type:
            emergencies = emergencies.filter(event_type=event_type)
        
        responded = request.query_params.get('responded')
        if responded is not None:
            if responded.lower() == 'true':
                emergencies = emergencies.filter(first_responder__isnull=False)
            else:
                emergencies = emergencies.filter(first_responder__isnull=True)
        
        emergencies = emergencies.order_by('-created_at')
        
        serializer = EmergencyEventSerializer(emergencies, many=True)
        return Response({
            'emergencies': serializer.data,
            'count': emergencies.count()
        }, status=status.HTTP_200_OK)


class EmergencyEventRespondView(APIView):
    """
    Respond to an emergency event
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['Emergencies'],
        summary='Respond to emergency',
        description='Mark an emergency event as responded to by a caregiver',
        request={'application/json': {'type': 'object', 'properties': {'response_notes': {'type': 'string'}}}},
        responses={200: EmergencyEventSerializer, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
    def post(self, request, emergency_id):
        try:
            emergency = EmergencyEvent.objects.get(id=emergency_id)
            
            # Verify user has access
            household = emergency.device.get_household()
            if household != request.user.household:
                return Response(
                    {'error': 'You do not have permission to respond to this emergency'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Verify user is a caregiver
            if not request.user.is_caregiver():
                return Response(
                    {'error': 'Only caregivers can respond to emergencies'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Mark as responded
            response_notes = request.data.get('response_notes', '')
            emergency.mark_as_responded(request.user, response_notes)
            
            serializer = EmergencyEventSerializer(emergency)
            return Response({
                'message': 'Emergency response recorded successfully',
                'emergency': serializer.data
            }, status=status.HTTP_200_OK)
            
        except EmergencyEvent.DoesNotExist:
            return Response(
                {'error': 'Emergency event not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to respond to emergency: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

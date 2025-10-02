from django.contrib.auth import get_user_model
from firebase_admin import auth
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()


class FirebaseAuthentication(BaseAuthentication):
    """
    DRF Authentication backend for Firebase tokens.
    Does not support anonymous users - all requests must be authenticated.
    """
    
    def authenticate(self, request):
        """
        Authenticate the request using Firebase ID token from Authorization header.
        Returns None if no auth header is present (letting DRF handle the 401).
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return None
        
        id_token = auth_header.split('Bearer ')[1]
        
        try:
            # Verify the Firebase token
            decoded_token = auth.verify_id_token(id_token)
            firebase_uid = decoded_token.get('uid')
            
            # Get the user from database
            try:
                user = User.objects.get(firebase_uid=firebase_uid)
                
                if not user.is_active:
                    raise AuthenticationFailed('User account is disabled')
                
                return (user, None)
                
            except User.DoesNotExist:
                raise AuthenticationFailed('User not found')
                
        except auth.InvalidIdTokenError:
            raise AuthenticationFailed('Invalid authentication token')
        except auth.ExpiredIdTokenError:
            raise AuthenticationFailed('Authentication token has expired')
        except Exception as e:
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')
    
    def authenticate_header(self, request):
        """
        Return the WWW-Authenticate header for 401 responses
        """
        return 'Bearer realm="api"'

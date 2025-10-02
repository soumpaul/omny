from drf_spectacular.extensions import OpenApiAuthenticationExtension


class FirebaseAuthenticationScheme(OpenApiAuthenticationExtension):
    """
    OpenAPI authentication extension for Firebase authentication
    """
    target_class = 'authentication.middleware.FirebaseAuthentication'
    name = 'FirebaseAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'Firebase ID Token',
            'description': 'Firebase ID token obtained from Firebase Authentication. Include as: Authorization: Bearer <token>'
        }

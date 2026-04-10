"""
Microsoft Entra ID (Azure AD) JWT token authentication for Django REST Framework.

Validates Bearer tokens issued by Entra against Microsoft's JWKS endpoint,
checks audience/issuer claims, and maps the token to a Django user.
"""

import json
import requests
import jwt
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

_jwks_cache = {}


def _get_signing_keys(tenant_id):
    """Fetch and cache Microsoft's public signing keys for token verification."""
    if tenant_id in _jwks_cache:
        return _jwks_cache[tenant_id]

    openid_url = (
        f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"
    )
    openid_config = requests.get(openid_url, timeout=10).json()
    jwks_uri = openid_config['jwks_uri']
    jwks = requests.get(jwks_uri, timeout=10).json()

    signing_keys = {}
    for key_data in jwks.get('keys', []):
        kid = key_data['kid']
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key_data))
        signing_keys[kid] = public_key

    _jwks_cache[tenant_id] = signing_keys
    return signing_keys


class EntraTokenAuthentication(BaseAuthentication):
    """
    Authenticates requests bearing a Microsoft Entra ID JWT access token.

    Expects header:  Authorization: Bearer <token>
    """

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ', 1)[1]
        tenant_id = settings.ENTRA_TENANT_ID
        client_id = settings.ENTRA_CLIENT_ID

        if not tenant_id or not client_id:
            raise AuthenticationFailed(
                'Entra ID is not configured. Set ENTRA_TENANT_ID and ENTRA_CLIENT_ID.'
            )

        try:
            # Decode header to get the key id
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid')

            signing_keys = _get_signing_keys(tenant_id)
            public_key = signing_keys.get(kid)
            if not public_key:
                # Keys may have rotated — clear cache and retry once
                _jwks_cache.pop(tenant_id, None)
                signing_keys = _get_signing_keys(tenant_id)
                public_key = signing_keys.get(kid)
                if not public_key:
                    raise AuthenticationFailed('Token signing key not found.')

            issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"

            payload = jwt.decode(
                token,
                key=public_key,
                algorithms=['RS256'],
                audience=settings.ENTRA_AUDIENCE,
                issuer=issuer,
            )

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired.')
        except jwt.InvalidAudienceError:
            raise AuthenticationFailed('Token audience mismatch.')
        except jwt.InvalidIssuerError:
            raise AuthenticationFailed('Token issuer mismatch.')
        except jwt.PyJWTError as e:
            raise AuthenticationFailed(f'Invalid token: {e}')

        # Map token to Django user
        user = self._get_or_create_user(payload)
        return (user, payload)

    def _get_or_create_user(self, payload):
        """Create or update a Django user from Entra token claims."""
        # 'oid' is the stable object identifier in Entra
        entra_oid = payload.get('oid', '')
        email = payload.get('preferred_username', '') or payload.get('email', '')
        name = payload.get('name', '')

        if not email:
            raise AuthenticationFailed('Token missing user email claim.')

        username = email.split('@')[0]

        user, created = User.objects.update_or_create(
            email=email,
            defaults={
                'username': username,
                'first_name': name.split(' ')[0] if name else '',
                'last_name': ' '.join(name.split(' ')[1:]) if name else '',
            },
        )
        return user

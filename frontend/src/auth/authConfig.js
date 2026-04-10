/**
 * Microsoft Entra ID (Azure AD) configuration for MSAL.
 *
 * Update these values with your Entra App Registration details:
 *  - VITE_ENTRA_CLIENT_ID:  Application (client) ID
 *  - VITE_ENTRA_TENANT_ID:  Directory (tenant) ID
 *  - VITE_ENTRA_REDIRECT_URI: Redirect URI (default: http://localhost:5173)
 */

const clientId = import.meta.env.VITE_ENTRA_CLIENT_ID || '';
const tenantId = import.meta.env.VITE_ENTRA_TENANT_ID || '';
const redirectUri = import.meta.env.VITE_ENTRA_REDIRECT_URI || 'http://localhost:5173';

export const msalConfig = {
  auth: {
    clientId,
    authority: `https://login.microsoftonline.com/${tenantId}`,
    redirectUri,
    postLogoutRedirectUri: redirectUri,
  },
  cache: {
    cacheLocation: 'localStorage',
    storeAuthStateInCookie: false,
  },
};

// Scopes to request when acquiring tokens for the backend API
export const apiScopes = {
  scopes: [`api://${clientId}/access_as_user`],
};

export const loginRequest = {
  scopes: ['openid', 'profile', 'email'],
};

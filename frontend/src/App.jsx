import React, { useEffect } from 'react';
import {
  AuthenticatedTemplate,
  UnauthenticatedTemplate,
  useMsal,
} from '@azure/msal-react';
import { apiScopes, loginRequest } from './auth/authConfig';
import { setTokenAcquirer } from './api/client';
import Layout from './components/Layout';

function AuthenticatedApp() {
  const { instance, accounts } = useMsal();

  useEffect(() => {
    // Wire up the API client to use MSAL for token acquisition
    setTokenAcquirer(async () => {
      if (accounts.length === 0) return null;
      try {
        const response = await instance.acquireTokenSilent({
          ...apiScopes,
          account: accounts[0],
        });
        return response.accessToken;
      } catch {
        // Silent acquisition failed — trigger interactive
        const response = await instance.acquireTokenPopup(apiScopes);
        return response.accessToken;
      }
    });
  }, [instance, accounts]);

  const user = accounts[0];
  const userName = user?.name || user?.username || 'User';

  return <Layout userName={userName} onLogout={() => instance.logoutRedirect()} />;
}

function LoginScreen() {
  const { instance } = useMsal();

  return (
    <div className="login-screen">
      <div className="login-card">
        <svg width="64" height="64" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
          <rect x="0" y="0" width="200" height="200" fill="#ffffff" />
          <rect x="10" y="10" width="180" height="180" fill="#000000" />
          <path d="M30,25 L80,25 L80,40 L52,40 L52,55 L75,55 L75,70 L52,70 L52,90 L36,90 L36,40 L30,40 Z" fill="#ffffff" />
          <circle cx="140" cy="57" r="33" fill="#ffffff" />
          <circle cx="140" cy="57" r="17" fill="#000000" />
          <path d="M28,110 L44,110 L55,127 L66,110 L82,110 L65,137 L82,164 L66,164 L55,147 L44,164 L28,164 L45,137 Z" fill="#ffffff" />
          <path d="M108,110 L145,110 C166,110 178,124 178,137 C178,150 166,164 145,164 L108,164 Z M124,126 L124,148 L143,148 C153,148 160,144 160,137 C160,130 153,126 143,126 Z" fill="#ffffff" />
        </svg>
        <h1>Tool Inventory</h1>
        <p>Sign in with your company account to manage tools across projects and sites.</p>
        <button className="btn btn-primary btn-lg" onClick={() => instance.loginRedirect(loginRequest)}>
          Sign in with Microsoft
        </button>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <>
      <AuthenticatedTemplate>
        <AuthenticatedApp />
      </AuthenticatedTemplate>
      <UnauthenticatedTemplate>
        <LoginScreen />
      </UnauthenticatedTemplate>
    </>
  );
}

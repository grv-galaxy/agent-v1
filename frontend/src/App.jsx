import { useCallback, useEffect, useState } from 'react';
import NetworkBanner from './components/NetworkBanner.jsx';
import SplashScreen from './components/SplashScreen.jsx';
import OnboardingPage from './pages/OnboardingPage.jsx';
import ChatPage from './pages/ChatPage.jsx';

const CONFIG_ENDPOINT = `${
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
}/api/config`;

const PROVIDER_LABELS = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  gemini: 'Google Gemini',
  'google-gemini': 'Google Gemini',
  mistral: 'Mistral',
  groq: 'Groq',
};

function normalizeProvider(provider) {
  return (provider || '').trim().toLowerCase().replace(/_/g, '-');
}

function getProviderLabel(provider) {
  return PROVIDER_LABELS[normalizeProvider(provider)] || provider || 'Provider';
}

function createChatProvider(config) {
  const provider = config?.provider || '';
  return {
    provider,
    providerLabel: config?.providerLabel || getProviderLabel(provider),
    apiKey: config?.apiKey || '',
    modelName: config?.modelName || config?.model || '',
    memoryEnabled: config?.memoryEnabled ?? config?.memory_enabled ?? true,
    useSeparateMemoryProvider:
      config?.useSeparateMemoryProvider ?? config?.use_separate_memory_provider ?? false,
    memoryProvider: config?.memoryProvider || config?.memory_provider || '',
    memoryModel: config?.memoryModel || config?.memory_model || '',
    hasMemoryApiKey: config?.hasMemoryApiKey ?? config?.has_memory_api_key ?? false,
    memoryApiKey: config?.memoryApiKey || '',
  };
}

function getInitialOnlineState() {
  return typeof navigator === 'undefined' ? true : navigator.onLine;
}

export default function App() {
  const [appState, setAppState] = useState('splash');
  const [splashState, setSplashState] = useState(() =>
    getInitialOnlineState() ? 'connecting' : 'offline',
  );
  const [isSplashExiting, setIsSplashExiting] = useState(false);
  const [verifiedProvider, setVerifiedProvider] = useState(null);
  const [isOnline, setIsOnline] = useState(getInitialOnlineState);
  const [networkBanner, setNetworkBanner] = useState(() =>
    getInitialOnlineState()
      ? { state: 'hidden', lostAt: null }
      : { state: 'offline', lostAt: Date.now() },
  );
  const [onlineRestoredAt, setOnlineRestoredAt] = useState(null);

  const showOnboarding = useCallback(() => {
    setIsSplashExiting(true);
    window.setTimeout(() => {
      setAppState('onboarding');
      setIsSplashExiting(false);
    }, 220);
  }, []);

  const showChat = useCallback((providerConfig) => {
    setVerifiedProvider(createChatProvider(providerConfig));
    setIsSplashExiting(true);
    window.setTimeout(() => {
      setAppState('chat');
      setIsSplashExiting(false);
    }, 220);
  }, []);

  const runStartupCheck = useCallback(() => {
    if (!getInitialOnlineState()) {
      setSplashState('offline');
      setAppState('splash');
      return undefined;
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 3000);
    const checkingTimer = window.setTimeout(() => setSplashState('checking'), 800);

    setAppState('splash');
    setIsSplashExiting(false);
    setSplashState('connecting');

    async function loadConfig() {
      try {
        const response = await fetch(CONFIG_ENDPOINT, { signal: controller.signal });
        const data = await response.json();

        window.clearTimeout(checkingTimer);

        if (!response.ok || data?.success === false) {
          throw new Error(data?.message || 'Unable to load configuration.');
        }

        if (data?.isConfigured) {
          setSplashState('success');
          window.setTimeout(
            () =>
              showChat({
                provider: data.provider,
                modelName: data.model,
                memory_enabled: data.memory_enabled,
                use_separate_memory_provider: data.use_separate_memory_provider,
                memory_provider: data.memory_provider,
                memory_model: data.memory_model,
                has_memory_api_key: data.has_memory_api_key,
              }),
            600,
          );
          return;
        }

        setSplashState('redirecting');
        window.setTimeout(showOnboarding, 400);
      } catch {
        window.clearTimeout(checkingTimer);
        setSplashState(getInitialOnlineState() ? 'backend-error' : 'offline');
      } finally {
        window.clearTimeout(timeout);
      }
    }

    loadConfig();

    return () => {
      window.clearTimeout(timeout);
      window.clearTimeout(checkingTimer);
      controller.abort();
    };
  }, [showChat, showOnboarding]);

  useEffect(() => runStartupCheck(), [runStartupCheck]);

  useEffect(() => {
    function handleOffline() {
      const lostAt = Date.now();
      setIsOnline(false);
      setNetworkBanner({ state: 'offline', lostAt });
    }

    function handleOnline() {
      setIsOnline(true);
      setOnlineRestoredAt(Date.now());
      setNetworkBanner((current) => ({ state: 'online', lostAt: current.lostAt }));
      window.setTimeout(() => {
        setNetworkBanner((current) =>
          current.state === 'online' ? { state: 'hidden', lostAt: null } : current,
        );
      }, 2500);

      if (appState === 'splash' && splashState === 'offline') {
        runStartupCheck();
      }
    }

    window.addEventListener('offline', handleOffline);
    window.addEventListener('online', handleOnline);

    return () => {
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('online', handleOnline);
    };
  }, [appState, runStartupCheck, splashState]);

  function handleVerified(providerConfig) {
    setVerifiedProvider(createChatProvider(providerConfig));
    setAppState('chat');
  }

  function handleProviderUpdate(providerConfig) {
    setVerifiedProvider((currentProvider) => ({
      ...(currentProvider || {}),
      ...createChatProvider({
        ...(currentProvider || {}),
        ...providerConfig,
      }),
    }));
  }

  function handleOnboardingBackendLost() {
    setAppState('splash');
    setIsSplashExiting(false);
    setSplashState(isOnline ? 'backend-error' : 'offline');
  }

  const appContent =
    appState === 'splash' ? (
      <SplashScreen
        state={splashState}
        exiting={isSplashExiting}
        onRetry={runStartupCheck}
        onEnterManually={showOnboarding}
      />
    ) : appState === 'onboarding' || !verifiedProvider ? (
      <div className="app-route-fade min-h-screen">
        <OnboardingPage
          onVerified={handleVerified}
          onBackendConnectionLost={handleOnboardingBackendLost}
        />
      </div>
    ) : (
      <div className="app-route-fade min-h-screen">
        <ChatPage
          provider={verifiedProvider}
          onProviderUpdate={handleProviderUpdate}
          isOnline={isOnline}
          onlineRestoredAt={onlineRestoredAt}
        />
      </div>
    );

  return (
    <>
      <NetworkBanner state={networkBanner.state} lostAt={networkBanner.lostAt} />
      {appContent}
    </>
  );
}

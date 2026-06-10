import { useEffect, useMemo, useRef, useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const CONFIG_ENDPOINT = `${API_BASE_URL}/api/config`;
const VERIFY_ENDPOINT =
  import.meta.env.VITE_VERIFY_PROVIDER_URL || `${API_BASE_URL}/api/verify-provider`;

function OpenAiLogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <circle cx="10" cy="10" r="9" fill="#0B0D12" />
      <path
        d="M9.9 3.3c1.1 0 2.1.6 2.7 1.5.9-.1 1.9.3 2.5 1.1.6.9.7 2 .2 2.9.6.7.8 1.8.4 2.8-.3 1-1.2 1.7-2.2 1.9-.4.9-1.3 1.5-2.3 1.7-1 .1-2-.3-2.6-1.1-1 .1-1.9-.3-2.5-1.1-.6-.9-.7-2-.2-2.9-.6-.7-.8-1.8-.4-2.8.3-1 1.2-1.7 2.2-1.9.4-.9 1.2-1.5 2.2-1.7Zm-1 3.2 3.2 1.8V6.8c0-.9-.7-1.6-1.6-1.7-.7-.1-1.3.2-1.6.8Zm4.3 1.3v3.7l1.2-.7c.8-.5 1-1.5.6-2.3-.3-.6-1-1-1.8-.7Zm-.6 4.8L9.4 14.4l1.2.7c.8.4 1.8.2 2.3-.5.4-.6.4-1.4-.3-2ZM7.8 14.1v-3.7l-1.2.7c-.8.5-1 1.5-.6 2.3.3.6 1 .9 1.8.7Zm-.6-6.7 3.2-1.8-1.2-.7c-.8-.4-1.8-.2-2.3.5-.4.6-.4 1.4.3 2Zm.7 1.1v3l2.6 1.5 2.6-1.5v-3L10.5 7Z"
        fill="#F8FAFC"
      />
    </svg>
  );
}

function AnthropicLogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#D97757" />
      <path d="m6.1 14 3.7-8h1.1l3.8 8h-1.6l-.8-1.8H8.4L7.6 14Zm2.8-3.1h2.8L10.3 7.7Z" fill="#1A1D27" />
    </svg>
  );
}

function GeminiLogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <path d="M18.2 10.2c0-.6-.1-1.1-.2-1.6h-7.7v3.1h4.4c-.2 1-.8 1.8-1.6 2.4v2h2.6c1.5-1.4 2.5-3.4 2.5-5.9Z" fill="#4285F4" />
      <path d="M10.3 18.1c2.2 0 4-.7 5.4-2l-2.6-2c-.7.5-1.6.8-2.8.8-2.1 0-3.9-1.4-4.5-3.3H3.1v2.1c1.4 2.6 4.1 4.4 7.2 4.4Z" fill="#34A853" />
      <path d="M5.8 11.6c-.2-.5-.3-1-.3-1.6s.1-1.1.3-1.6V6.3H3.1c-.6 1.1-.9 2.4-.9 3.7s.3 2.6.9 3.7Z" fill="#FBBC04" />
      <path d="M10.3 5.1c1.2 0 2.3.4 3.1 1.2l2.3-2.3c-1.4-1.3-3.2-2.1-5.4-2.1-3.1 0-5.8 1.8-7.2 4.4l2.7 2.1c.6-1.9 2.4-3.3 4.5-3.3Z" fill="#EA4335" />
    </svg>
  );
}

function MistralLogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#FF7000" />
      <path d="M5 15V5h2.2v4h1.7V5h2.2v4h1.7V5H15v10h-2.2v-4h-1.7v4H8.9v-4H7.2v4Z" fill="#111827" />
    </svg>
  );
}

function GroqLogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#6D28D9" />
      <path
        d="M10 4.2a5.8 5.8 0 1 0 5.8 5.8h-2.2A3.6 3.6 0 1 1 10 6.4c1 0 1.9.4 2.5 1.1l-2.1 2.1H16V4l-1.9 1.9A5.8 5.8 0 0 0 10 4.2Z"
        fill="#F8FAFC"
      />
    </svg>
  );
}

function AI21Logo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#111827" />
      <path d="M5 5.4h10v2.1H9.2v1.4h4.9V11H9.2v1.5H15v2.1H5Z" fill="#F8FAFC" />
      <path d="M6.9 14.6 12.5 5.4h2.6l-5.6 9.2Z" fill="#37D5C8" opacity="0.95" />
      <text
        x="9.2"
        y="12.3"
        fill="#111827"
        fontFamily="Arial, sans-serif"
        fontSize="5.2"
        fontWeight="700"
      >
        21
      </text>
    </svg>
  );
}

function CerebrasLogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#FFF7ED" />
      <path d="M5 5h4v4H5Zm6 0h4v4h-4ZM5 11h4v4H5Zm6 0h4v4h-4Z" fill="#111827" />
      <path d="M7 7h6v6H7Z" fill="#EF4444" />
    </svg>
  );
}

function CohereLogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#F6E7C8" />
      <circle cx="7.2" cy="7.5" r="3.3" fill="#39594D" />
      <circle cx="12.5" cy="7.1" r="2.5" fill="#D86F45" />
      <circle cx="11.3" cy="12.6" r="3.6" fill="#EAB308" />
    </svg>
  );
}

function DeepInfraLogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#0B1020" />
      <path d="M4.5 14.7 8.2 5.3h3.2l-2 5h2.7L15.5 5.3h-3.1L8.7 14.7Z" fill="#38BDF8" />
      <path d="M7.4 14.7h5.2l2.9-7.3h-2.7l-2 5H8.4Z" fill="#A78BFA" />
    </svg>
  );
}

function DeepSeekLogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#2563EB" />
      <path
        d="M4.3 10.4c0-3 2.2-5.3 5.3-5.3 3.7 0 6.1 2.9 6.1 6.3 0 2.1-1.1 3.5-2.9 3.5-.9 0-1.6-.3-2.1-.9-.7.6-1.5.9-2.5.9-2.2 0-3.9-1.8-3.9-4.5Z"
        fill="#EFF6FF"
      />
      <path
        d="M8 8.3c1.1-.9 2.8-.9 4 .2m-4.3 3.3c1 .8 2.7.9 3.9.1"
        fill="none"
        stroke="#2563EB"
        strokeLinecap="round"
        strokeWidth="1.3"
      />
    </svg>
  );
}

function FireworksAILogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#111827" />
      <path d="M10 3.9v4.2M10 11.9v4.2M3.9 10h4.2M11.9 10h4.2" stroke="#F97316" strokeLinecap="round" strokeWidth="1.8" />
      <path d="m5.7 5.7 3 3M11.3 11.3l3 3M14.3 5.7l-3 3M8.7 11.3l-3 3" stroke="#FACC15" strokeLinecap="round" strokeWidth="1.8" />
      <circle cx="10" cy="10" r="1.7" fill="#F8FAFC" />
    </svg>
  );
}

function HuggingFaceLogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#FFD21E" />
      <circle cx="7.2" cy="8" r="1.1" fill="#3F2A12" />
      <circle cx="12.8" cy="8" r="1.1" fill="#3F2A12" />
      <path d="M6.4 12.1c1.9 1.7 5.3 1.7 7.2 0" fill="none" stroke="#3F2A12" strokeLinecap="round" strokeWidth="1.3" />
      <path d="M4.7 12.1c-.8.3-1.4-.1-1.5-.8-.1-.8.4-1.4 1.2-1.6M15.3 12.1c.8.3 1.4-.1 1.5-.8.1-.8-.4-1.4-1.2-1.6" fill="none" stroke="#3F2A12" strokeLinecap="round" strokeWidth="1.2" />
    </svg>
  );
}

function NvidiaNimLogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#76B900" />
      <path
        d="M4.3 10.2c1.7-2.2 3.6-3.3 5.8-3.3 2.1 0 3.9 1 5.6 3.1-1.7 2.1-3.6 3.2-5.7 3.2-2.2 0-4.1-1-5.7-3Z"
        fill="#111827"
      />
      <path d="M7.1 10.1a3 3 0 1 0 6 0 3 3 0 0 0-6 0Z" fill="#F8FAFC" />
      <circle cx="10.1" cy="10.1" r="1.5" fill="#111827" />
    </svg>
  );
}

function OpenRouterLogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#0F172A" />
      <path d="M4.3 6h7.4l3.9 4-3.9 4H4.3l3.9-4Z" fill="#F8FAFC" />
      <path d="M8.6 8h3l2 2-2 2h-3l2-2Z" fill="#38BDF8" />
    </svg>
  );
}

function TogetherAILogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#18181B" />
      <path d="M6.4 6.7h7.2M6.4 13.3h7.2M10 6.7v6.6" stroke="#F8FAFC" strokeLinecap="round" strokeWidth="1.6" />
      <circle cx="6.4" cy="6.7" r="2" fill="#14B8A6" />
      <circle cx="13.6" cy="6.7" r="2" fill="#8B5CF6" />
      <circle cx="6.4" cy="13.3" r="2" fill="#F59E0B" />
      <circle cx="13.6" cy="13.3" r="2" fill="#F8FAFC" />
    </svg>
  );
}

export const PROVIDERS = [
  { id: 'openai', label: 'OpenAI', placeholder: 'gpt-4.1-mini', Logo: OpenAiLogo },
  { id: 'gemini', label: 'Gemini', placeholder: 'gemini-1.5-pro', Logo: GeminiLogo },
  { id: 'anthropic', label: 'Anthropic', placeholder: 'claude-3-5-sonnet-latest', Logo: AnthropicLogo },
  { id: 'mistral', label: 'Mistral', placeholder: 'mistral-large-latest', Logo: MistralLogo },
  { id: 'ai21', label: 'AI21', placeholder: 'jamba-large', Logo: AI21Logo },
  { id: 'cerebras', label: 'Cerebras', placeholder: 'llama-3.3-70b', Logo: CerebrasLogo },
  { id: 'cohere', label: 'Cohere', placeholder: 'command-r-plus', Logo: CohereLogo },
  { id: 'deepinfra', label: 'DeepInfra', placeholder: 'meta-llama/Meta-Llama-3.1-70B-Instruct', Logo: DeepInfraLogo },
  { id: 'deepseek', label: 'DeepSeek', placeholder: 'deepseek-chat', Logo: DeepSeekLogo },
  { id: 'fireworksai', label: 'Fireworks AI', placeholder: 'accounts/fireworks/models/llama-v3p1-70b-instruct', Logo: FireworksAILogo },
  { id: 'groq', label: 'Groq', placeholder: 'llama-3.3-70b-versatile', Logo: GroqLogo },
  { id: 'huggingface', label: 'Hugging Face', placeholder: 'meta-llama/Llama-3.1-8B-Instruct', Logo: HuggingFaceLogo },
  { id: 'nvidianim', label: 'NVIDIA NIM', placeholder: 'meta/llama-3.1-70b-instruct', Logo: NvidiaNimLogo },
  { id: 'openrouter', label: 'OpenRouter', placeholder: 'openai/gpt-4o-mini', Logo: OpenRouterLogo },
  { id: 'togetherai', label: 'Together AI', placeholder: 'meta-llama/Llama-3.3-70B-Instruct-Turbo', Logo: TogetherAILogo },
];

export function FieldIcon({ name, className = 'h-4 w-4' }) {
  const common = {
    fill: 'none',
    stroke: 'currentColor',
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    strokeWidth: '1.6',
  };

  const paths = {
    chevron: <path d="m4 6 4 4 4-4" {...common} />,
    eye: (
      <>
        <path d="M1.8 8s2.1-4 6.2-4 6.2 4 6.2 4-2.1 4-6.2 4-6.2-4-6.2-4Z" {...common} />
        <circle cx="8" cy="8" r="1.7" {...common} />
      </>
    ),
    eyeOff: (
      <path d="m2.2 2.2 11.6 11.6M6.2 4.4A6.1 6.1 0 0 1 8 4c4.1 0 6.2 4 6.2 4a9.8 9.8 0 0 1-1.8 2.3M9.7 11.7A6.2 6.2 0 0 1 8 12c-4.1 0-6.2-4-6.2-4a10 10 0 0 1 2.6-2.9" {...common} />
    ),
    pencil: (
      <>
        <path d="M3.5 11.8 4 9.2 10.6 2.6a1.4 1.4 0 0 1 2 2L6 11.2l-2.5.6Z" {...common} />
        <path d="m9.5 3.7 2.8 2.8" {...common} />
      </>
    ),
    check: <path d="m3.5 8.2 2.8 2.8 6.2-6.2" {...common} />,
    x: (
      <>
        <path d="m4.5 4.5 7 7" {...common} />
        <path d="m11.5 4.5-7 7" {...common} />
      </>
    ),
  };

  return (
    <svg viewBox="0 0 16 16" className={className} aria-hidden="true">
      {paths[name]}
    </svg>
  );
}

export function Spinner() {
  return (
    <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[#6366F1]/30 border-t-[#6366F1]" />
  );
}

function normalizeProvider(provider) {
  return (provider || '').trim().toLowerCase().replace(/[_\s]+/g, '-');
}

const PROVIDER_ALIASES = {
  'ai-21': 'ai21',
  'deep-infra': 'deepinfra',
  'deep-seek': 'deepseek',
  fireworks: 'fireworksai',
  'fireworks-ai': 'fireworksai',
  'google-gemini': 'gemini',
  'hugging-face': 'huggingface',
  nvidia: 'nvidianim',
  'nvidia-nim': 'nvidianim',
  'open-router': 'openrouter',
  'together-ai': 'togetherai',
};

export function isNetworkError(error) {
  return (
    error?.name === 'TypeError' ||
    error?.name === 'AbortError' ||
    /failed to fetch|networkerror|load failed/i.test(error?.message || '')
  );
}

export function findProvider(provider) {
  const normalized = normalizeProvider(provider);
  if (!normalized) {
    return null;
  }
  const providerKey = PROVIDER_ALIASES[normalized] || normalized;

  return (
    PROVIDERS.find((item) => normalizeProvider(item.id) === providerKey) ||
    PROVIDERS.find((item) => normalizeProvider(item.label) === providerKey) ||
    PROVIDERS.find((item) => {
      const providerId = normalizeProvider(item.id);
      const providerLabel = normalizeProvider(item.label);
      return (
        providerId.includes(providerKey) ||
        providerKey.includes(providerId) ||
        providerLabel.includes(providerKey) ||
        providerKey.includes(providerLabel)
      );
    }) ||
    null
  );
}

export function ProviderSelect({ value, onChange, disabled = false }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const selectedProvider = findProvider(value);
  const SelectedLogo = selectedProvider?.Logo;

  useEffect(() => {
    function handlePointerDown(event) {
      if (!dropdownRef.current?.contains(event.target)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        disabled={disabled}
        onClick={() => setIsOpen((current) => !current)}
        className="flex h-11 w-full items-center justify-between rounded-[8px] border border-[#2A2A2A] bg-[#1A1A1A] px-3 text-left text-sm text-[#E8E8E8] outline-none transition duration-150 hover:border-[#3A3A3A] focus:border-[#6366F1] disabled:cursor-not-allowed disabled:opacity-40"
      >
        <span className="flex items-center gap-3">
          {SelectedLogo ? <SelectedLogo /> : <span className="h-5 w-5 rounded-[5px] bg-[#242424]" />}
          <span className={selectedProvider ? 'text-[#E8E8E8]' : 'text-[#555555]'}>
            {selectedProvider?.label || 'Select provider'}
          </span>
        </span>
        <FieldIcon
          name="chevron"
          className={`h-4 w-4 text-[#666666] transition duration-150 ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {isOpen ? (
        <div
          role="listbox"
          className="absolute z-30 mt-2 w-full overflow-hidden rounded-[8px] border border-[#2A2A2A] bg-[#1A1A1A] p-1 shadow-2xl shadow-black/40"
        >
          {PROVIDERS.map((provider) => {
            const Logo = provider.Logo;
            const active = selectedProvider?.id === provider.id;

            return (
              <button
                key={provider.id}
                type="button"
                role="option"
                aria-selected={active}
                onClick={() => {
                  onChange(provider.id);
                  setIsOpen(false);
                }}
                className={`flex h-10 w-full items-center gap-3 rounded-[6px] px-3 text-left text-sm transition duration-150 ${
                  active
                    ? 'bg-[#6366F1]/15 text-[#E8E8E8]'
                    : 'text-[#A0A0A0] hover:bg-[#242424] hover:text-[#E8E8E8]'
                }`}
              >
                <Logo />
                <span>{provider.label}</span>
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

export function FieldLabel({ children }) {
  return <label className="mb-2 block text-[13px] text-[#94A3B8]">{children}</label>;
}

export default function LLMConfigCard({
  onConfigSaved,
  isOnline = true,
  onBackendConnectionLost,
  configFetchGuardRef,
}) {
  const [provider, setProvider] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('');
  const [apiKeyExists, setApiKeyExists] = useState(false);
  const [apiKeyLocked, setApiKeyLocked] = useState(true);
  const [hasChanged, setHasChanged] = useState(false);
  const [editedFields, setEditedFields] = useState({
    provider: false,
    model: false,
    apiKey: false,
  });
  const initialValues = useRef({
    provider: '',
    model: '',
    apiKeyExists: false,
  });
  const [showApiKey, setShowApiKey] = useState(false);
  const [isLoadingConfig, setIsLoadingConfig] = useState(true);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [testStatus, setTestStatus] = useState(null);
  const [saveStatus, setSaveStatus] = useState(null);
  const localConfigFetchedRef = useRef(false);
  const configFetchedRef = configFetchGuardRef || localConfigFetchedRef;

  const selectedProvider = useMemo(() => findProvider(provider) || PROVIDERS[0], [provider]);
  const apiInputValue = apiKeyLocked && apiKeyExists && !editedFields.apiKey
    ? '................'
    : apiKey;
  const canTestConnection =
    Boolean(provider) &&
    Boolean(model.trim()) &&
    (apiKeyExists || editedFields.apiKey) &&
    !isTesting &&
    !isLoadingConfig;

  useEffect(() => {
    setHasChanged(Object.values(editedFields).some(Boolean));
  }, [editedFields]);

  useEffect(() => {
    if (configFetchedRef.current) {
      setIsLoadingConfig(false);
      return undefined;
    }
    configFetchedRef.current = true;
    let ignore = false;

    async function loadConfig() {
      setIsLoadingConfig(true);
      try {
        const response = await fetch(CONFIG_ENDPOINT);
        const data = await response.json();
        if (!response.ok || data?.success === false) {
          throw new Error(data?.message || 'Unable to load configuration.');
        }

        const nextProvider = data.provider ? (findProvider(data.provider)?.id || data.provider) : '';
        const nextModel = data.model || '';
        const nextHasApiKey = Boolean(data.hasApiKey || data.isConfigured);

        if (!ignore) {
          initialValues.current = {
            provider: nextProvider,
            model: nextModel,
            apiKeyExists: nextHasApiKey,
          };
          setProvider(nextProvider);
          setModel(nextModel);
          setApiKeyExists(nextHasApiKey);
          setApiKey('');
          setApiKeyLocked(true);
          setEditedFields({
            provider: false,
            model: false,
            apiKey: false,
          });
          setTestStatus(null);
        }
      } catch (error) {
        if (!ignore) {
          setTestStatus({
            type: 'error',
            message: error?.message || 'Unable to load configuration.',
          });
        }
      } finally {
        if (!ignore) {
          setIsLoadingConfig(false);
        }
      }
    }

    loadConfig();
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    if (testStatus?.type !== 'success') {
      return undefined;
    }

    const timeout = window.setTimeout(() => setTestStatus(null), 3000);
    return () => window.clearTimeout(timeout);
  }, [testStatus]);

  useEffect(() => {
    if (saveStatus?.type !== 'success') {
      return undefined;
    }

    const timeout = window.setTimeout(() => setSaveStatus(null), 2000);
    return () => window.clearTimeout(timeout);
  }, [saveStatus]);

  useEffect(() => {
    if (isOnline && saveStatus?.message === 'No internet connection. Changes not saved.') {
      setSaveStatus(null);
    }
  }, [isOnline, saveStatus]);

  function updateProvider(nextProvider) {
    setProvider(nextProvider);
    setEditedFields((current) => ({ ...current, provider: true }));
    setTestStatus(null);
    setSaveStatus(null);
  }

  function updateApiKey(nextApiKey) {
    setApiKey(nextApiKey);
    setEditedFields((current) => ({ ...current, apiKey: true }));
    setTestStatus(null);
    setSaveStatus(null);
  }

  function updateModel(nextModel) {
    setModel(nextModel);
    setEditedFields((current) => ({ ...current, model: true }));
    setTestStatus(null);
    setSaveStatus(null);
  }

  function createVerifyPayload() {
    return {
      provider,
      api_key: editedFields.apiKey ? apiKey : '',
      model_name: model.trim(),
    };
  }

  function createSavePayload() {
    const payload = {
      provider,
      model_name: model.trim(),
    };

    if (editedFields.apiKey) {
      payload.api_key = apiKey.trim();
    }

    return payload;
  }

  async function testConnection() {
    setIsTesting(true);
    setTestStatus(null);
    try {
      const response = await fetch(VERIFY_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(createVerifyPayload()),
      });
      const data = await response.json();

      if (!response.ok || !data?.success) {
        throw new Error(data?.message || 'Connection failed.');
      }

      setTestStatus({ type: 'success', message: 'Connected successfully' });
    } catch (error) {
      if (isOnline && isNetworkError(error)) {
        onBackendConnectionLost?.();
      }
      setTestStatus({
        type: 'error',
        message: error?.message || 'Connection failed.',
      });
    } finally {
      setIsTesting(false);
    }
  }

  async function saveChanges() {
    if (isSaving) {
      return;
    }

    if (!isOnline) {
      setSaveStatus({
        type: 'error',
        message: 'No internet connection. Changes not saved.',
      });
      return;
    }

    setIsSaving(true);
    setSaveStatus(null);
    try {
      const response = await fetch(CONFIG_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(createSavePayload()),
      });
      const data = await response.json();

      if (!response.ok || !data?.success) {
        throw new Error(data?.message || 'Unable to save changes.');
      }

      const nextApiKeyExists = editedFields.apiKey ? Boolean(apiKey.trim()) : apiKeyExists;
      initialValues.current = {
        provider,
        model: model.trim(),
        apiKeyExists: nextApiKeyExists,
      };
      setApiKeyExists(nextApiKeyExists);
      setApiKey('');
      setApiKeyLocked(true);
      setEditedFields({
        provider: false,
        model: false,
        apiKey: false,
      });
      setSaveStatus({ type: 'success', message: 'Saved' });
      onConfigSaved?.({
        provider,
        providerLabel: findProvider(provider)?.label || provider,
        apiKey: '',
        modelName: model.trim(),
      });
    } catch (error) {
      if (isOnline && isNetworkError(error)) {
        onBackendConnectionLost?.();
      }
      setSaveStatus({
        type: 'error',
        message: error?.message || 'Unable to save changes.',
      });
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div>
      <div
        className={`rounded-[10px] border border-[#1F1F1F] bg-[#111111] p-6 transition-opacity duration-200 ${
          isLoadingConfig ? 'opacity-50' : 'opacity-100'
        }`}
      >
        <div className="flex flex-col gap-5">
          <div>
            <FieldLabel>Provider</FieldLabel>
            <ProviderSelect value={provider} onChange={updateProvider} />
          </div>

          <div>
            <FieldLabel>API Key</FieldLabel>
            <div className="flex items-center gap-2">
              <div className="relative min-w-0 flex-1">
                <input
                  type={showApiKey ? 'text' : 'password'}
                  value={apiInputValue}
                  readOnly={apiKeyLocked}
                  onChange={(event) => updateApiKey(event.target.value)}
                  placeholder="Enter provider API key"
                  autoComplete="off"
                  className={`h-11 w-full rounded-[8px] px-3 pr-10 text-sm outline-none transition duration-150 placeholder:text-[#555555] ${
                    apiKeyLocked
                      ? 'border border-[#1F1F1F] bg-[#0D0D0D] text-[#666666]'
                      : 'border border-[#6366F1] bg-[#1A1A1A] text-[#E8E8E8]'
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey((current) => !current)}
                  className="absolute right-2 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-[6px] text-[#666666] transition duration-150 hover:bg-[#242424] hover:text-[#E8E8E8]"
                  aria-label={showApiKey ? 'Hide API key' : 'Show API key'}
                >
                  <FieldIcon name={showApiKey ? 'eyeOff' : 'eye'} />
                </button>
              </div>
              <button
                type="button"
                onClick={() => {
                  setApiKeyLocked(false);
                  setApiKey('');
                  setEditedFields((current) => ({ ...current, apiKey: true }));
                  setTestStatus(null);
                  setSaveStatus(null);
                }}
                className="grid h-9 w-9 shrink-0 place-items-center rounded-[8px] border border-[#2A2A2A] text-[#888888] transition duration-150 hover:border-[#6366F1] hover:text-[#6366F1]"
                aria-label="Edit API key"
                title="Edit API key"
              >
                <FieldIcon name="pencil" />
              </button>
            </div>
            <p className="mt-2 text-[12px] text-[#555555]">
              Your API key is stored locally in .env and never sent to any server.
            </p>
          </div>

          <div>
            <FieldLabel>Model name</FieldLabel>
            <input
              type="text"
              value={model}
              onChange={(event) => updateModel(event.target.value)}
              placeholder={selectedProvider.placeholder}
              className="h-11 w-full rounded-[8px] border border-[#2A2A2A] bg-[#1A1A1A] px-3 text-sm text-[#E8E8E8] outline-none transition duration-150 placeholder:text-[#555555] hover:border-[#3A3A3A] focus:border-[#6366F1]"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={testConnection}
              disabled={!canTestConnection}
              className="flex h-9 items-center gap-2 rounded-[8px] border border-[#2A2A2A] bg-transparent px-4 text-[13px] text-[#E8E8E8] transition duration-150 hover:border-[#6366F1] hover:text-[#6366F1] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {isTesting ? <Spinner /> : null}
              Test Connection
            </button>

            {testStatus ? (
              <div
                className={`flex items-center gap-1.5 text-[13px] ${
                  testStatus.type === 'success' ? 'text-[#22C55E]' : 'text-[#EF4444]'
                }`}
              >
                <FieldIcon name={testStatus.type === 'success' ? 'check' : 'x'} />
                <span>{testStatus.message}</span>
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={saveChanges}
          disabled={isSaving || isLoadingConfig}
          className="h-9 rounded-[8px] bg-[#6366F1] px-5 text-[14px] text-white transition duration-150 hover:bg-[#4F46E5] disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isSaving ? 'Saving' : 'Save changes'}
        </button>
        {saveStatus ? (
          <span
            className={`text-[13px] ${
              saveStatus.type === 'success' ? 'text-[#22C55E]' : 'text-[#EF4444]'
            }`}
          >
            {saveStatus.message}
          </span>
        ) : null}
      </div>
    </div>
  );
}

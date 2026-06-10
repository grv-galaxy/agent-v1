import { useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import ProviderField from '../components/ProviderField.jsx';
import Spinner from '../components/Spinner.jsx';

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
      <rect width="20" height="20" rx="5" fill="#FAB50F" />
      <path
        d="M6.2 15V5h1.8l2.6 5.2L13 5h1.8v10h-1.8V7.6L10.8 13l-2.2-5.4v7.4H6.2Z"
        fill="#000"
      />
    </svg>
  );
}

function CerebrasLogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#000" />
      <circle cx="7" cy="7" r="2" fill="#fff" />
      <circle cx="13" cy="7" r="2" fill="#fff" />
      <path d="M7 9c-1.1 0-2 .9-2 2v2h10v-2c0-1.1-.9-2-2-2H7Z" fill="#fff" />
    </svg>
  );
}

function CohereLogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#1E40AF" />
      <path
        d="M10 3c3.9 0 7 3.1 7 7s-3.1 7-7 7-7-3.1-7-7 3.1-7 7-7Zm0 2c-2.8 0-5 2.2-5 5s2.2 5 5 5 5-2.2 5-5-2.2-5-5-5Z"
        fill="#fff"
      />
    </svg>
  );
}

function DeepInfraLogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#2563EB" />
      <path
        d="M5 8h2v4H5V8Zm4-2h2v6h-2V6Zm4 2h2v4h-2V8Z"
        fill="#fff"
      />
    </svg>
  );
}

function DeepSeekLogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#0F172A" />
      <path
        d="M10 4c3.3 0 6 2.7 6 6s-2.7 6-6 6-6-2.7-6-6 2.7-6 6-6Zm0 2c-2.2 0-4 1.8-4 4s1.8 4 4 4 4-1.8 4-4-1.8-4-4-4Z"
        fill="#38BDF8"
      />
    </svg>
  );
}

function FireworksAILogo() {
  return (
    <svg viewBox="0 0 20 20" className="h-5 w-5" aria-hidden="true">
      <rect width="20" height="20" rx="5" fill="#7C3AED" />
      <path
        d="M10 3v14M5 8h10M5 12h10"
        stroke="#fff"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
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

function EyeOpenIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4" aria-hidden="true">
      <path
        d="M1.8 8s2.1-4 6.2-4 6.2 4 6.2 4-2.1 4-6.2 4-6.2-4-6.2-4Z"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.4"
      />
      <circle cx="8" cy="8" r="1.7" fill="none" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}

function EyeClosedIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4" aria-hidden="true">
      <path
        d="m2.2 2.2 11.6 11.6M6.2 4.4A6.1 6.1 0 0 1 8 4c4.1 0 6.2 4 6.2 4a9.8 9.8 0 0 1-1.8 2.3M9.7 11.7A6.2 6.2 0 0 1 8 12c-4.1 0-6.2-4-6.2-4a10 10 0 0 1 2.6-2.9"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.4"
      />
    </svg>
  );
}

const PROVIDERS = [
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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const VERIFY_ENDPOINT =
  import.meta.env.VITE_VERIFY_PROVIDER_URL || `${API_BASE_URL}/api/verify-provider`;

function ProviderDropdown({ providers, selectedProvider, onSelect }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const SelectedLogo = selectedProvider.Logo;

  useEffect(() => {
    function handlePointerDown(event) {
      if (!dropdownRef.current?.contains(event.target)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, []);

  function selectProvider(nextProvider) {
    onSelect(nextProvider.id);
    setIsOpen(false);
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        id="provider"
        type="button"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((value) => !value)}
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            setIsOpen(false);
          }
        }}
        className="flex h-12 w-full items-center justify-between rounded-[8px] border border-[#2A2D3A] bg-[#12141C] px-4 text-left text-sm text-[#F1F5F9] outline-none transition duration-150 hover:border-[#3A3D4A] focus:border-[#6366F1] focus:ring-4 focus:ring-[#6366F1]/15"
      >
        <span className="flex items-center gap-3">
          <SelectedLogo />
          <span>{selectedProvider.label}</span>
        </span>
        <span className={`text-[#64748B] transition duration-150 ${isOpen ? 'rotate-180' : ''}`} aria-hidden="true">
          <svg viewBox="0 0 16 16" className="h-4 w-4">
            <path d="m4 6 4 4 4-4" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" />
          </svg>
        </span>
      </button>

      {isOpen ? (
        <div
          role="listbox"
          aria-labelledby="provider"
          className="absolute z-20 mt-2 w-full rounded-[8px] border border-[#2A2D3A] bg-[#12141C] shadow-2xl shadow-black/35 max-h-[300px] overflow-y-auto scrollbar-thin scrollbar-thumb-[#2A2D3A] scrollbar-track-transparent hover:scrollbar-thumb-[#3A3D4A]"
        >
          <div className="p-1">
            {providers.map((item) => {
              const Logo = item.Logo;
              const isSelected = item.id === selectedProvider.id;

              return (
                <button
                  key={item.id}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => selectProvider(item)}
                  className={`flex h-10 w-full items-center gap-3 rounded-[6px] px-3 text-left text-sm transition duration-150 ${
                    isSelected
                      ? 'bg-[#6366F1]/12 text-[#F1F5F9]'
                      : 'text-[#94A3B8] hover:bg-[#1A1D27] hover:text-[#F1F5F9]'
                  }`}
                >
                  <Logo />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function OnboardingPage({ onVerified, onBackendConnectionLost }) {
  const [provider, setProvider] = useState(PROVIDERS[0].id);
  const [apiKey, setApiKey] = useState('');
  const [modelName, setModelName] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const selectedProvider = useMemo(
    () => PROVIDERS.find((item) => item.id === provider) ?? PROVIDERS[0],
    [provider],
  );

  async function handleSubmit(event) {
    event.preventDefault();

    if (!apiKey.trim() || !modelName.trim()) {
      setErrorMessage('Enter an API key and model name to continue.');
      return;
    }

    setIsVerifying(true);
    setErrorMessage('');

    try {
      const response = await axios.post(VERIFY_ENDPOINT, {
        provider: selectedProvider.id,
        api_key: apiKey.trim(),
        model_name: modelName.trim(),
      });

      if (!response.data?.success) {
        setErrorMessage(response.data?.message || 'Verification failed.');
        return;
      }

      try {
        await fetch(`${API_BASE_URL}/api/config`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            provider: selectedProvider.id,
            api_key: apiKey.trim(),
            model_name: modelName.trim(),
          }),
        });
      } catch (error) {
        console.error('Failed to save config:', error);
      }

      onVerified({
        provider: selectedProvider.id,
        providerLabel: selectedProvider.label,
        apiKey: apiKey.trim(),
        modelName: modelName.trim(),
      });
    } catch (error) {
      if (!error?.response) {
        onBackendConnectionLost?.();
      }
      const responseMessage = error?.response?.data?.message;
      setErrorMessage(
        responseMessage ||
          'Verification failed. Check the provider, API key, and model name.',
      );
    } finally {
      setIsVerifying(false);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#0F1117] px-5 py-8 font-['Inter',ui-sans-serif,system-ui] text-[#F1F5F9]">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(99,102,241,0.18),transparent_36%)]" />

      <section className="relative w-full max-w-[500px] rounded-[8px] border border-[#2A2D3A] bg-[#1A1D27] p-6 shadow-2xl shadow-black/25 transition duration-150 sm:p-8">
        <div className="mb-7 space-y-3">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-[#6366F1]">
            Provider setup
          </p>
          <h1 className="text-[28px] font-semibold leading-tight text-[#F1F5F9]">
            Connect your LLM
          </h1>
          <p className="text-sm leading-6 text-[#64748B]">
            Verify a provider before opening the chat workspace.
          </p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <ProviderField id="provider" label="Provider">
            <ProviderDropdown
              providers={PROVIDERS}
              selectedProvider={selectedProvider}
              onSelect={(nextProvider) => {
                setProvider(nextProvider);
                setErrorMessage('');
              }}
            />
          </ProviderField>

          <ProviderField
            id="api-key"
            label="API key"
            hint="The key is only used for this verification request."
          >
            <div className="relative">
              <input
                id="api-key"
                type={showApiKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(event) => {
                  setApiKey(event.target.value);
                  setErrorMessage('');
                }}
                placeholder="Enter provider API key"
                autoComplete="off"
                className="h-12 w-full rounded-[8px] border border-[#2A2D3A] bg-[#12141C] px-4 pr-11 text-sm text-[#F1F5F9] outline-none transition duration-150 placeholder:text-[#64748B] hover:border-[#3A3D4A] focus:border-[#6366F1] focus:ring-4 focus:ring-[#6366F1]/15"
              />
              <button
                type="button"
                onClick={() => setShowApiKey((value) => !value)}
                className="absolute right-3 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-[6px] text-[#64748B] transition duration-150 hover:text-[#F1F5F9] focus:outline-none focus:ring-2 focus:ring-[#6366F1]/30"
                aria-label={showApiKey ? 'Hide API key' : 'Show API key'}
              >
                {showApiKey ? <EyeClosedIcon /> : <EyeOpenIcon />}
              </button>
            </div>
          </ProviderField>

          <ProviderField
            id="model-name"
            label="Model name"
            hint={`Example for ${selectedProvider.label}: ${selectedProvider.placeholder}`}
          >
            <input
              id="model-name"
              type="text"
              value={modelName}
              onChange={(event) => {
                setModelName(event.target.value);
                setErrorMessage('');
              }}
              placeholder={selectedProvider.placeholder}
              className="h-12 w-full rounded-[8px] border border-[#2A2D3A] bg-[#12141C] px-4 text-sm text-[#F1F5F9] outline-none transition duration-150 placeholder:text-[#64748B] hover:border-[#3A3D4A] focus:border-[#6366F1] focus:ring-4 focus:ring-[#6366F1]/15"
            />
          </ProviderField>

          {errorMessage ? (
            <div
              className="rounded-[8px] border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm leading-6 text-red-200"
              role="alert"
            >
              {errorMessage}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={isVerifying}
            className="flex h-12 w-full items-center justify-center gap-2 rounded-[8px] bg-[#6366F1] px-4 text-sm font-semibold text-white transition duration-150 hover:bg-[#4F46E5] focus:outline-none focus:ring-4 focus:ring-[#6366F1]/25 disabled:cursor-not-allowed disabled:bg-[#2A2D3A] disabled:text-[#64748B]"
          >
            {isVerifying ? (
              <>
                <Spinner />
                Verifying
              </>
            ) : (
              'Verify'
            )}
          </button>
        </form>
      </section>
    </main>
  );
}

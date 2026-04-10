'use client';

import { useTripStore } from '@/store/useTripStore';
import { Cpu, ChevronDown } from 'lucide-react';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const providers = [
  {
    id: 'groq',
    name: 'Groq (Ultra Fast)',
    models: [
      { id: 'llama-3.1-8b-instant', name: 'Llama 3.1 8B' },
      { id: 'llama-3.3-70b-versatile', name: 'Llama 3.3 70B' },
    ],
  },
  {
    id: 'openrouter',
    name: 'OpenRouter (Diverse)',
    models: [
      { id: 'nvidia/nemotron-3-nano-30b-a3b:free', name: 'Nemotron 30B (Free)' },
      { id: 'mistralai/mistral-7b-instruct:free', name: 'Mistral 7B (Free)' },
      { id: 'meta-llama/llama-3.1-8b-instruct:free', name: 'Llama 3.1 8B (Free)' },
    ],
  },
];

export function ModelSelector() {
  const { input, setInput } = useTripStore();
  const [isOpen, setIsOpen] = useState(false);

  const selectedModel = providers
    .flatMap((p) => p.models)
    .find((m) => m.id === input.model) || providers[1].models[0];

  const handleSelect = (providerId: string, modelId: string) => {
    setInput({ provider: providerId, model: modelId });
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-3 px-4 py-2 bg-charcoal-lighter border border-border rounded-xl text-offwhite hover:border-amber transition-all"
      >
        <Cpu className="w-4 h-4 text-amber" />
        <span className="text-sm font-medium">{selectedModel.name}</span>
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <div 
              className="fixed inset-0 z-40" 
              onClick={() => setIsOpen(false)} 
            />
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="absolute right-0 bottom-full mb-2 w-72 bg-charcoal-lighter border border-border rounded-2xl shadow-2xl z-50 overflow-hidden"
            >
              <div className="p-4 bg-charcoal/50 border-b border-border">
                <span className="text-xs font-bold text-amber uppercase tracking-wider">
                  Select AI Power
                </span>
              </div>
              <div className="max-h-80 overflow-y-auto">
                {providers.map((provider) => (
                  <div key={provider.id} className="p-2">
                    <div className="px-3 py-1 text-[10px] font-bold text-offwhite-muted uppercase">
                      {provider.name}
                    </div>
                    {provider.models.map((model) => (
                      <button
                        key={model.id}
                        onClick={() => handleSelect(provider.id, model.id)}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                          input.model === model.id
                            ? 'bg-amber text-charcoal font-bold'
                            : 'text-offwhite hover:bg-white/5'
                        }`}
                      >
                        {model.name}
                      </button>
                    ))}
                  </div>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

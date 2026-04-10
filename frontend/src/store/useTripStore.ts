import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { TripState, TripInput, TripResult } from '@/types';

const defaultInput: Partial<TripInput> = {
  destinations: ['Cairo & Giza'],
  budget: '1000-2000 EGP',
  groupSize: 2,
  startDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
  endDate: new Date(Date.now() + 31 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
  travelStyles: ['Historical', 'Food & Dining'],
  historicalKnowledge: 'Beginner',
  preferredTimePeriods: ['Pharaonic', 'Islamic'],
  museumVisits: true,
  waterActivities: false,
  accommodationType: 'Medium',
  transportation: 'Private Car',
  foodPreferences: 'Vegetarian',
  tripPace: 'Moderate',
  mustVisit: 'Pyramids',
  model: 'nvidia/nemotron-3-nano-30b-a3b:free',
  provider: 'openrouter',
};

export const useTripStore = create<TripState>()(
  persist(
    (set, get) => ({
      input: defaultInput,
      result: null,
      isLoading: false,
      currentStep: 0,
      favorites: [],

      setInput: (input) =>
        set((state) => ({
          input: { ...state.input, ...input },
        })),

      setResult: (result) =>
        set({ result }),

      setLoading: (isLoading) =>
        set({ isLoading }),

      setCurrentStep: (step) =>
        set({ currentStep: step }),

      toggleFavorite: (name) =>
        set((state) => {
          const exists = state.favorites.includes(name);
          return {
            favorites: exists
              ? state.favorites.filter((f) => f !== name)
              : [...state.favorites, name],
          };
        }),

      isFavorite: (name) =>
        get().favorites.includes(name),

      reset: () =>
        set({
          input: defaultInput,
          result: null,
          isLoading: false,
          currentStep: 0,
        }),
    }),
    {
      name: 'egypt-trip-storage',
      partialize: (state) => ({
        favorites: state.favorites,
        input: state.input,
      }),
    }
  )
);

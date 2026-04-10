'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Hero } from '@/components/hero/Hero';
import { Wizard } from '@/components/wizard/Wizard';
import { LoadingState } from '@/components/loading/LoadingState';
import { ResultsHero } from '@/components/results/ResultsHero';
import { OverviewCard } from '@/components/results/OverviewCard';
import { PlaceCard } from '@/components/results/PlaceCard';
import { RestaurantCard } from '@/components/results/RestaurantCard';
import { HotelSection } from '@/components/results/HotelSection';
import { ItineraryTimeline } from '@/components/results/ItineraryTimeline';
import { BudgetChart } from '@/components/results/BudgetChart';
import { TipsSection } from '@/components/results/TipsSection';
import { ExportBar } from '@/components/results/ExportBar';
import { MobileNav } from '@/components/results/MobileNav';
import { useTripStore } from '@/store/useTripStore';
import { generateTrip } from '@/lib/api';
import { TripInput, TripResult } from '@/types';

type AppView = 'hero' | 'wizard' | 'loading' | 'results' | 'error';

function parseTripPlanText(text: string): Partial<TripResult> {
  const result: Partial<TripResult> = {
    overview: '',
    places: [],
    restaurants: [],
    hotels: [],
    itinerary: [],
    budget: {
      accommodation: 0,
      food: 0,
      activities: 0,
      transportation: 0,
      total: 0,
      currency: 'EGP',
    },
    tips: [],
  };

  const sections = text.split(/##\s+/).filter(Boolean);

  for (const section of sections) {
    const [title, ...contentLines] = section.split('\n');
    const content = contentLines.join('\n').trim();

    if (title.toLowerCase().includes('overview') || title.toLowerCase().includes('introduction')) {
      result.overview = content;
    } else if (title.toLowerCase().includes('place')) {
      const placeRegex = /\*\*(.+?)\*\*(?:\s*\(([^)]*)\))?/g;
      let match;
      while ((match = placeRegex.exec(content)) !== null) {
        result.places!.push({
          name: match[1].trim(),
          city: match[2]?.trim(),
        });
      }
    } else if (title.toLowerCase().includes('restaurant')) {
      const restRegex = /\*\*(.+?)\*\*(?:\s*\(([^)]*)\))?/g;
      let match;
      while ((match = restRegex.exec(content)) !== null) {
        result.restaurants!.push({
          name: match[1].trim(),
          city: match[2]?.trim(),
        });
      }
    } else if (title.toLowerCase().includes('hotel')) {
      const hotelRegex = /\*\*(.+?)\*\*(?:\s*\(([^)]*)\))?/g;
      let match;
      while ((match = hotelRegex.exec(content)) !== null) {
        result.hotels!.push({
          name: match[1].trim(),
          city: match[2]?.trim(),
        });
      }
    } else if (title.toLowerCase().includes('day') || title.toLowerCase().includes('itinerary')) {
      const dayLines = content.split('\n').filter(Boolean);
      let currentDay: any = null;
      for (const line of dayLines) {
        const dayMatch = line.match(/\*\*Day\s*(\d+)/i);
        if (dayMatch) {
          if (currentDay) result.itinerary!.push(currentDay);
          currentDay = { day: parseInt(dayMatch[1]), date: '', morning: undefined, lunch: undefined, afternoon: undefined, dinner: undefined };
        } else if (currentDay) {
          if (!currentDay._desc) currentDay._desc = [];
          currentDay._desc.push(line.replace(/^- /, '').replace(/\*\*/g, ''));
        }
      }
      if (currentDay) result.itinerary!.push(currentDay);

      if (result.itinerary!.length > 0) {
        result.itinerary = result.itinerary!.map((day: any) => ({
          ...day,
          morning: {
            place: 'Day Activities',
            description: (day._desc || []).slice(0, 2).join('. '),
          },
          afternoon: {
            place: 'Afternoon Exploration',
            description: (day._desc || []).slice(2, 4).join('. '),
          },
        }));
      }
    } else if (title.toLowerCase().includes('budget') || title.toLowerCase().includes('cost')) {
      const amountMatch = content.match(/(\d+)\s*EGP/);
      if (amountMatch) {
        const total = parseInt(amountMatch[1]);
        result.budget = {
          accommodation: Math.round(total * 0.4),
          food: Math.round(total * 0.25),
          activities: Math.round(total * 0.2),
          transportation: Math.round(total * 0.15),
          total,
          currency: 'EGP',
        };
      }
    } else if (title.toLowerCase().includes('tip') || title.toLowerCase().includes('advice')) {
      const tipLines = content.split('\n').filter((l) => l.trim().startsWith('-') || l.trim().startsWith('*'));
      result.tips = tipLines.map((l) => l.replace(/^[-*]\s*/, '').trim()).filter(Boolean);
    }
  }

  if (!result.overview && sections.length > 0) {
    result.overview = sections[0].split('\n').slice(1).join('\n').trim();
  }

  return result;
}

export default function Home() {
  const [view, setView] = useState<AppView>('hero');
  const [activeSection, setActiveSection] = useState('places');
  const [error, setError] = useState<string | null>(null);
  const { input, setInput, setResult, setLoading, result } = useTripStore();

  const handleStartPlanning = useCallback(() => {
    setView('wizard');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const handleGenerate = useCallback(async () => {
    setView('loading');
    setLoading(true);
    setError(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });

    try {
      const tripInput: TripInput = {
        destinations: input.destinations || ['Cairo & Giza'],
        budget: input.budget || '1000-2000 EGP',
        groupSize: input.groupSize || 2,
        startDate: input.startDate || '',
        endDate: input.endDate || '',
        travelStyles: input.travelStyles || ['Historical', 'Food & Dining'],
        historicalKnowledge: input.historicalKnowledge || 'Beginner',
        preferredTimePeriods: input.preferredTimePeriods || ['Pharaonic', 'Islamic'],
        museumVisits: input.museumVisits ?? true,
        waterActivities: input.waterActivities ?? false,
        accommodationType: input.accommodationType || 'Medium',
        transportation: input.transportation || 'Private Car',
        foodPreferences: input.foodPreferences || 'Vegetarian',
        tripPace: input.tripPace || 'Moderate',
        mustVisit: input.mustVisit || 'Pyramids',
        model: input.model,
        provider: input.provider,
      };

      const tripResult = await generateTrip(tripInput);
      setResult(tripResult);
      setView('results');
    } catch (error: any) {
      console.error('Trip generation failed:', error);
      setError(error.message || 'Failed to generate trip. Please try again.');
      setView('error');
    } finally {
      setLoading(false);
    }
  }, [input, setResult, setLoading]);

  const handleNavigate = useCallback((section: string) => {
    setActiveSection(section);
    const el = document.getElementById(section);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, []);

  const handleRetry = useCallback(() => {
    setError(null);
    setView('wizard');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  return (
    <div className="min-h-screen bg-charcoal">
      <AnimatePresence mode="wait">
        {view === 'hero' && (
          <motion.div
            key="hero"
            exit={{ opacity: 0, y: -50 }}
            transition={{ duration: 0.5 }}
          >
            <Hero onStartPlanning={handleStartPlanning} />
          </motion.div>
        )}

        {view === 'wizard' && (
          <motion.div
            key="wizard"
            initial={{ opacity: 0, x: 100 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -100 }}
            transition={{ duration: 0.5 }}
          >
            <Wizard onGenerate={handleGenerate} />
          </motion.div>
        )}

        {view === 'loading' && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          >
            <LoadingState
              tripSummary={{
                destinations: input.destinations || ['Cairo & Giza'],
                dates: `${input.startDate || ''} - ${input.endDate || ''}`,
                groupSize: input.groupSize || 2,
                budget: input.budget || '1000-2000 EGP',
              }}
            />
          </motion.div>
        )}

        {view === 'error' && (
          <motion.div
            key="error"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="min-h-screen bg-charcoal flex flex-col items-center justify-center px-4">
              <div className="glass-card p-8 max-w-md w-full text-center">
                <div className="text-5xl mb-6">⚠️</div>
                <h2 className="text-2xl font-bold text-offwhite mb-3">Something went wrong</h2>
                <p className="text-offwhite-muted mb-2">Trip generation failed</p>
                {error && (
                  <p className="text-red-400 text-sm mb-6 bg-red-400/10 rounded-lg p-3">{error}</p>
                )}
                <p className="text-offwhite-muted text-sm mb-6">
                  The AI backend may be starting up or experiencing high load. This can take 30-60 seconds on first request.
                </p>
                <button
                  onClick={handleRetry}
                  className="w-full py-3 px-6 bg-amber hover:bg-amber/90 text-charcoal font-semibold rounded-lg transition-colors"
                >
                  Try Again
                </button>
              </div>
            </div>
          </motion.div>
        )}

        {view === 'results' && result && (
          <motion.div
            key="results"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="pb-32 md:pb-20"
          >
            <ResultsHero
              destinations={input.destinations || ['Cairo & Giza']}
              startDate={input.startDate || ''}
              endDate={input.endDate || ''}
              groupSize={input.groupSize || 2}
              budget={input.budget || '1000-2000 EGP'}
              tripPace={input.tripPace || 'Moderate'}
            />

            <div className="max-w-6xl mx-auto px-4 py-12 space-y-16">
              {result.overview && (
                <section id="overview">
                  <OverviewCard description={result.overview} />
                </section>
              )}

              {result.places.length > 0 && (
                <section id="places">
                  <h2 className="section-title text-3xl font-bold mb-8">
                    Places to Visit
                  </h2>
                  <div className="flex gap-6 overflow-x-auto pb-4 snap-x snap-mandatory scrollbar-hide">
                    {result.places.map((place, index) => (
                      <PlaceCard key={place.name} place={place} index={index} />
                    ))}
                  </div>
                </section>
              )}

              {result.restaurants.length > 0 && (
                <section id="restaurants">
                  <h2 className="section-title text-3xl font-bold mb-8">
                    Restaurants & Dining
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {result.restaurants.map((restaurant, index) => (
                      <RestaurantCard
                        key={restaurant.name}
                        restaurant={restaurant}
                        index={index}
                      />
                    ))}
                  </div>
                </section>
              )}

              {result.hotels.length > 0 && (
                <section id="hotels">
                  <h2 className="section-title text-3xl font-bold mb-8">
                    Where to Stay
                  </h2>
                  <HotelSection hotels={result.hotels} />
                </section>
              )}

              {result.itinerary.length > 0 && (
                <section id="itinerary">
                  <h2 className="section-title text-3xl font-bold mb-8">
                    Day-by-Day Itinerary
                  </h2>
                  <ItineraryTimeline days={result.itinerary} />
                </section>
              )}

              {result.budget && result.budget.total > 0 && (
                <section id="budget">
                  <h2 className="section-title text-3xl font-bold mb-8">
                    Budget Breakdown
                  </h2>
                  <BudgetChart
                    budget={result.budget}
                    totalBudget={parseInt((input.budget || '0').split('-')[0]) || undefined}
                  />
                </section>
              )}

              {result.tips.length > 0 && (
                <section id="tips">
                  <h2 className="section-title text-3xl font-bold mb-8">
                    Travel Tips
                  </h2>
                  <TipsSection tips={result.tips} />
                </section>
              )}
            </div>

            <ExportBar />
            <MobileNav activeSection={activeSection} onNavigate={handleNavigate} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export interface TripInput {
  destinations: string[];
  budget: string;
  groupSize: number;
  startDate: string;
  endDate: string;
  travelStyles: string[];
  historicalKnowledge: string;
  preferredTimePeriods: string[];
  museumVisits: boolean;
  waterActivities: boolean;
  accommodationType: string;
  transportation: string;
  foodPreferences: string;
  tripPace: string;
  mustVisit: string;
  model?: string;
  provider?: string;
}

export interface Place {
  name: string;
  address?: string;
  rating?: string;
  ticketPrice?: string;
  timings?: string;
  description?: string;
  city?: string;
  image?: string;
  imageUrl?: string;
}

export interface Restaurant {
  name: string;
  cuisines?: string;
  avgPrice?: string;
  location?: string;
  description?: string;
  city?: string;
  image?: string;
  imageUrl?: string;
}

export interface Hotel {
  name: string;
  rating?: string;
  price?: string;
  distanceKm?: string;
  description?: string;
  city?: string;
  image?: string;
  imageUrl?: string;
}

export interface TripResult {
  overview: string;
  places: Place[];
  restaurants: Restaurant[];
  hotels: Hotel[];
  itinerary: DayItinerary[];
  budget: BudgetBreakdown;
  tips: string[];
  summary?: string;
}

export interface DayItinerary {
  day: number;
  date: string;
  morning?: ActivityBlock;
  lunch?: ActivityBlock;
  afternoon?: ActivityBlock;
  dinner?: ActivityBlock;
  dayCost?: string;
}

export interface ActivityBlock {
  place: string;
  time?: string;
  description: string;
  price?: string;
  image?: string;
}

export interface BudgetBreakdown {
  accommodation: number;
  food: number;
  activities: number;
  transportation: number;
  total: number;
  currency: string;
}

export interface TripState {
  input: Partial<TripInput>;
  result: TripResult | null;
  isLoading: boolean;
  currentStep: number;
  favorites: string[];
  setInput: (input: Partial<TripInput>) => void;
  setResult: (result: TripResult | null) => void;
  setLoading: (loading: boolean) => void;
  setCurrentStep: (step: number) => void;
  toggleFavorite: (name: string) => void;
  isFavorite: (name: string) => boolean;
  reset: () => void;
}

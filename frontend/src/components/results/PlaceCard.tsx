'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Star, Bookmark, BookmarkCheck, ExternalLink } from 'lucide-react';
import { Place } from '@/types';
import { useTripStore } from '@/store/useTripStore';

interface PlaceCardProps {
  place: Place;
  index: number;
}

export function PlaceCard({ place, index }: PlaceCardProps) {
  const { toggleFavorite, isFavorite } = useTripStore();
  const [imageLoaded, setImageLoaded] = useState(false);

  const imageUrl =
    place.imageUrl ||
    `https://images.unsplash.com/photo-1539650116574-8efeb43e2750?w=600&q=80`;

  const rating = place.rating ? parseFloat(place.rating) : null;
  const stars = rating ? Math.round(rating) : 0;

  return (
    <motion.div
      className="glass-card overflow-hidden flex-shrink-0 w-72 group"
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.08 }}
    >
      <div className="relative h-48 overflow-hidden">
        {!imageLoaded && (
          <div className="absolute inset-0 bg-charcoal-lighter animate-pulse" />
        )}
        <img
          src={imageUrl}
          alt={place.name}
          className={`w-full h-48 object-cover transition-all duration-500 group-hover:scale-110 ${
            imageLoaded ? 'opacity-100' : 'opacity-0'
          }`}
          onLoad={() => setImageLoaded(true)}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-charcoal/80 to-transparent" />

        <button
          onClick={() => toggleFavorite(place.name)}
          className="absolute top-3 right-3 p-2 rounded-full bg-charcoal/60 backdrop-blur-sm hover:bg-charcoal/80 transition-colors"
        >
          {isFavorite(place.name) ? (
            <BookmarkCheck className="w-4 h-4 text-amber" />
          ) : (
            <Bookmark className="w-4 h-4 text-offwhite" />
          )}
        </button>

        <div className="absolute bottom-3 left-3 right-3">
          <h3 className="text-lg font-bold text-offwhite">{place.name}</h3>
        </div>
      </div>

      <div className="p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1">
            {rating !== null ? (
              <>
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    className={`w-4 h-4 ${
                      i < stars ? 'text-amber fill-amber' : 'text-offwhite-muted'
                    }`}
                  />
                ))}
                <span className="text-sm text-offwhite-muted ml-1">
                  {place.rating}
                </span>
              </>
            ) : (
              <span className="text-sm text-offwhite-muted">Not rated</span>
            )}
          </div>
          {place.ticketPrice && (
            <span className="px-2 py-1 rounded-full bg-amber/10 text-amber text-xs font-medium">
              {place.ticketPrice} EGP
            </span>
          )}
        </div>

        {place.description && (
          <p className="text-sm text-offwhite-muted line-clamp-2 mb-3">
            {place.description}
          </p>
        )}

        {place.address && (
          <a
            href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(place.address)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-amber hover:text-amber-light transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
            View on Maps
          </a>
        )}
      </div>
    </motion.div>
  );
}

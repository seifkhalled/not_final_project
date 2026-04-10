'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { ExternalLink } from 'lucide-react';
import { Restaurant } from '@/types';

interface RestaurantCardProps {
  restaurant: Restaurant;
  index: number;
}

export function RestaurantCard({ restaurant, index }: RestaurantCardProps) {
  const [imageLoaded, setImageLoaded] = useState(false);

  const imageUrl =
    restaurant.imageUrl ||
    `https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&q=80`;

  const cuisineTags = restaurant.cuisines
    ? restaurant.cuisines.split(',').map((c) => c.trim())
    : [];

  return (
    <motion.div
      className="glass-card overflow-hidden group relative"
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.08 }}
      whileHover={{ y: -4 }}
    >
      <div className="relative h-40 overflow-hidden">
        {!imageLoaded && (
          <div className="absolute inset-0 bg-charcoal-lighter animate-pulse" />
        )}
        <img
          src={imageUrl}
          alt={restaurant.name}
          className={`w-full h-40 object-cover transition-all duration-500 group-hover:scale-110 ${
            imageLoaded ? 'opacity-100' : 'opacity-0'
          }`}
          onLoad={() => setImageLoaded(true)}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-charcoal/80 to-transparent" />

        <div className="absolute bottom-3 left-3">
          <h3 className="text-lg font-bold text-offwhite">{restaurant.name}</h3>
        </div>
      </div>

      <div className="p-4">
        {cuisineTags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {cuisineTags.map((cuisine) => (
              <span
                key={cuisine}
                className="px-2 py-1 rounded-full bg-terracotta/20 text-terracotta-light text-xs font-medium"
              >
                {cuisine}
              </span>
            ))}
          </div>
        )}

        <div className="flex items-center justify-between">
          {restaurant.avgPrice && (
            <span className="text-sm text-amber font-medium">
              ~{restaurant.avgPrice} EGP
            </span>
          )}
          {restaurant.location && (
            <a
              href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(restaurant.location)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-amber hover:text-amber-light transition-colors"
            >
              <ExternalLink className="w-3 h-3" />
              View on Maps
            </a>
          )}
        </div>

        <p className="text-xs text-offwhite-muted mt-2 italic">
          * Cuisine tags are AI-generated and may not be accurate
        </p>
      </div>
    </motion.div>
  );
}

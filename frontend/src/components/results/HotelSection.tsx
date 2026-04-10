'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Star, Award } from 'lucide-react';
import { Hotel } from '@/types';

interface HotelSectionProps {
  hotels: Hotel[];
}

export function HotelSection({ hotels }: HotelSectionProps) {
  const [imageLoaded, setImageLoaded] = useState<Record<number, boolean>>({});

  if (hotels.length === 0) return null;

  const featuredHotel = hotels[0];
  const otherHotels = hotels.slice(1);

  return (
    <div className="space-y-6">
      {/* Featured Hotel */}
      <motion.div
        className="glass-card overflow-hidden"
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
      >
        <div className="grid grid-cols-1 md:grid-cols-2">
          <div className="relative h-64 md:h-auto overflow-hidden">
            {!imageLoaded[0] && (
              <div className="absolute inset-0 bg-charcoal-lighter animate-pulse" />
            )}
            <img
              src={
                featuredHotel.imageUrl ||
                `https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800&q=80`
              }
              alt={featuredHotel.name}
              className={`w-full h-full object-cover ${
                imageLoaded[0] ? 'opacity-100' : 'opacity-0'
              }`}
              onLoad={() => setImageLoaded((prev) => ({ ...prev, 0: true }))}
            />
            <div className="absolute top-4 left-4">
              <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-amber text-charcoal text-sm font-bold">
                <Award className="w-4 h-4" />
                Best Value
              </span>
            </div>
          </div>

          <div className="p-6 md:p-8 flex flex-col justify-center">
            <h3 className="text-2xl font-bold mb-2">{featuredHotel.name}</h3>

            <div className="flex items-center gap-2 mb-4">
              {featuredHotel.rating && featuredHotel.rating !== 'N/A' ? (
                <>
                  <div className="flex items-center gap-1">
                    {[...Array(5)].map((_, i) => (
                      <Star
                        key={i}
                        className={`w-4 h-4 ${
                          i < Math.round(parseFloat(featuredHotel.rating || '0') / 2)
                            ? 'text-amber fill-amber'
                            : 'text-offwhite-muted'
                        }`}
                      />
                    ))}
                  </div>
                  <span className="text-sm text-offwhite-muted">
                    {featuredHotel.rating}/10
                  </span>
                </>
              ) : (
                <span className="text-sm text-offwhite-muted">Rating unavailable</span>
              )}
            </div>

            {featuredHotel.price && (
              <div className="mb-4">
                <span className="text-2xl font-bold text-amber">
                  {featuredHotel.price} EGP
                </span>
                <span className="text-sm text-offwhite-muted ml-2">/ night</span>
              </div>
            )}

            {featuredHotel.distanceKm && (
              <p className="text-sm text-offwhite-muted">
                {featuredHotel.distanceKm} km from city center
              </p>
            )}
          </div>
        </div>
      </motion.div>

      {/* Other Hotels */}
      {otherHotels.length > 0 && (
        <div className="space-y-3">
          {otherHotels.map((hotel, index) => (
            <motion.div
              key={hotel.name}
              className="glass-card p-4 flex items-center justify-between"
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.08 }}
            >
              <div>
                <h4 className="font-semibold">{hotel.name}</h4>
                <div className="flex items-center gap-2 mt-1">
                  {hotel.rating && hotel.rating !== 'N/A' ? (
                    <span className="text-xs text-offwhite-muted">
                      {hotel.rating}/10
                    </span>
                  ) : (
                    <span className="text-xs text-offwhite-muted">Not rated</span>
                  )}
                </div>
              </div>
              {hotel.price && (
                <span className="text-amber font-bold">{hotel.price} EGP</span>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}

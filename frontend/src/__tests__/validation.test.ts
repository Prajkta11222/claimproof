import { describe, it, expect } from 'vitest';
import { z } from 'zod';

const incidentSchema = z.object({
  crop_name: z.string().min(1).max(60),
  location_lat: z.number().min(-90).max(90),
  location_lng: z.number().min(-180).max(180),
  area_affected_acres: z.number().positive().max(10000).optional(),
});

describe('Incident form zod validations', () => {
  it('validates a correct payload', () => {
    const valid = {
      crop_name: 'Chickpea',
      location_lat: 21.1458,
      location_lng: 79.0882,
      area_affected_acres: 2.5,
    };
    expect(incidentSchema.safeParse(valid).success).toBe(true);
  });

  it('rejects empty crop name', () => {
    const invalid = {
      crop_name: '',
      location_lat: 21.1458,
      location_lng: 79.0882,
    };
    expect(incidentSchema.safeParse(invalid).success).toBe(false);
  });

  it('rejects out of bounds latitude', () => {
    const invalid = {
      crop_name: 'Soybean',
      location_lat: 95.0,
      location_lng: 79.0882,
    };
    expect(incidentSchema.safeParse(invalid).success).toBe(false);
  });

  it('rejects zero or negative area affected', () => {
    const invalid = {
      crop_name: 'Cotton',
      location_lat: 21.1458,
      location_lng: 79.0882,
      area_affected_acres: 0,
    };
    expect(incidentSchema.safeParse(invalid).success).toBe(false);
  });
});

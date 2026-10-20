/** Shapes from `fikisha.ratings.services.job_ratings_view`. */
export type RatingSide = 'BUSINESS_RATES_OPERATOR' | 'OPERATOR_RATES_BUSINESS';

export interface RatingItem {
  id: string;
  side: RatingSide;
  score: number;
  published: boolean;
  counted: boolean;
  created_at: string;
  /** the rater's own, or staff */
  comment?: string;
}

export interface JobRatingsView {
  can_rate: boolean;
  side: RatingSide | null;
  closes_in_seconds?: number;
  mine?: RatingItem | null;
  about_me?: RatingItem | null;
  /** staff only */
  ratings?: RatingItem[];
}

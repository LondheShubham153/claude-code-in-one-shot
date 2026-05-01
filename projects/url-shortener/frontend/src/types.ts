export interface LinkOut {
  slug: string;
  url: string;
  short_url: string;
  click_count: number;
  disabled: boolean;
  created_at: string;
}

export interface ShortenRequest {
  url: string;
  custom_slug?: string;
}

export interface ApiError {
  message: string;
  status: number;
}

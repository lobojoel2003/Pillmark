// Types for the Pillmark API and helpers to move search criteria in and out of URLs.

import { isColorKey, isShapeKey, type ColorKey, type ShapeKey } from './vocab';

export interface PillSummary {
	id: number;
	set_id: string;
	product_code: string | null;
	name: string | null;
	generic_name: string | null;
	strength: string | null;
	dosage_form: string | null;
	imprint: string;
	imprint_sides: string[];
	colors: string[];
	shape: string | null;
	size_mm: number | null;
	score: number | null;
	has_symbol: boolean;
	labeler: string | null;
	marketed: boolean;
	dea_schedule: string | null;
	photo_url: string | null;
	label_image_url: string | null;
	match_score: number;
	group_size: number;
}

export interface Ingredient {
	name: string;
	strength: string | null;
	unii: string | null;
}

export interface LabelInfo {
	set_id: string;
	document_id: string | null;
	version: number;
	effective_date: string | null;
	title: string | null;
	labeler: string | null;
	kind: string;
	dailymed_url: string;
	images: string[];
}

export interface PillDetail extends PillSummary {
	route: string | null;
	ingredients: Ingredient[];
	packages: string[];
	marketing_start: string | null;
	marketing_end: string | null;
	label: LabelInfo;
}

export interface SearchResponse {
	total: number;
	limit: number;
	offset: number;
	results: PillSummary[];
	disclaimer: string;
}

export interface Meta {
	version: string;
	build: string;
	commit: string;
	dataset: {
		labels: number;
		pills: number;
		with_imprint: number;
		labelers: number;
		last_import: { source: string; finished_at: string | null } | null;
	} | null;
}

/** What the person has told us about the pill. */
export interface Criteria {
	imprint: string;
	noImprint: boolean;
	shape: ShapeKey | null;
	colors: ColorKey[];
	score: number | null;
	size: number | null;
	name: string;
}

export const MAX_COLORS = 2;
export const PAGE_SIZE = 24;

export function emptyCriteria(): Criteria {
	return {
		imprint: '',
		noImprint: false,
		shape: null,
		colors: [],
		score: null,
		size: null,
		name: ''
	};
}

export function hasCriteria(c: Criteria): boolean {
	return Boolean(
		c.imprint.trim() ||
		c.noImprint ||
		c.shape ||
		c.colors.length ||
		c.score ||
		c.size ||
		c.name.trim()
	);
}

function intIn(value: string | null, min: number, max: number): number | null {
	if (value === null || value.trim() === '') return null;
	const n = Number(value);
	return Number.isFinite(n) && n >= min && n <= max ? n : null;
}

/** Read criteria from page URL search params (unknown values are ignored). */
export function criteriaFromParams(params: URLSearchParams): Criteria {
	const colors = params
		.getAll('color')
		.flatMap((v) => v.split(','))
		.map((v) => v.trim().toLowerCase())
		.filter(isColorKey);
	const shape = (params.get('shape') ?? '').trim().toLowerCase();
	return {
		imprint: (params.get('imprint') ?? '').slice(0, 64),
		noImprint: params.get('imprint') === null && params.get('no_imprint') === '1',
		shape: isShapeKey(shape) ? shape : null,
		colors: [...new Set(colors)].slice(0, MAX_COLORS),
		score: intIn(params.get('score'), 1, 4),
		size: intIn(params.get('size'), 1, 40),
		name: (params.get('q') ?? '').slice(0, 100)
	};
}

/** Criteria as page URL search params (short, shareable, stable order). */
export function criteriaToParams(c: Criteria): URLSearchParams {
	const params = new URLSearchParams();
	if (c.imprint.trim()) params.set('imprint', c.imprint.trim());
	else if (c.noImprint) params.set('no_imprint', '1');
	if (c.shape) params.set('shape', c.shape);
	for (const color of c.colors) params.append('color', color);
	if (c.score) params.set('score', String(c.score));
	if (c.size) params.set('size', String(c.size));
	if (c.name.trim()) params.set('q', c.name.trim());
	return params;
}

/** Criteria as Pillmark API query params. */
export function criteriaToApiParams(c: Criteria, offset = 0, limit = PAGE_SIZE): URLSearchParams {
	const params = new URLSearchParams();
	if (c.imprint.trim()) params.set('imprint', c.imprint.trim());
	else if (c.noImprint) params.set('has_imprint', 'false');
	if (c.shape) params.set('shape', c.shape);
	for (const color of c.colors) params.append('color', color);
	if (c.score) params.set('score', String(c.score));
	if (c.size) params.set('size', String(c.size));
	if (c.name.trim()) params.set('q', c.name.trim());
	params.set('limit', String(limit));
	if (offset) params.set('offset', String(offset));
	return params;
}

export class ApiError extends Error {
	constructor(
		readonly status: number,
		message: string
	) {
		super(message);
	}
}

type Fetch = typeof fetch;

export async function getJson<T>(fetcher: Fetch, path: string): Promise<T> {
	let response: Response;
	try {
		response = await fetcher(`/api${path}`, { headers: { accept: 'application/json' } });
	} catch {
		throw new ApiError(503, 'The pill database is not reachable right now.');
	}
	if (!response.ok) {
		let message = `The pill database answered ${response.status}.`;
		try {
			const body = await response.json();
			if (typeof body?.detail === 'string') message = body.detail;
		} catch {
			// keep the generic message
		}
		throw new ApiError(response.status, message);
	}
	return (await response.json()) as T;
}

export function searchPills(fetcher: Fetch, c: Criteria, offset = 0): Promise<SearchResponse> {
	return getJson<SearchResponse>(fetcher, `/v1/pills?${criteriaToApiParams(c, offset)}`);
}

/** Human wording for how well a result matched the imprint. */
export function matchLabel(score: number, hasImprint: boolean): string | null {
	if (!hasImprint) return null;
	if (score >= 0.97) return 'Exact imprint';
	if (score >= 0.85) return 'Imprint matches';
	if (score >= 0.7) return 'Partial imprint';
	return 'Close imprint';
}

export function pillTitle(p: Pick<PillSummary, 'name' | 'generic_name'>): string {
	return p.name || p.generic_name || 'Unnamed product';
}

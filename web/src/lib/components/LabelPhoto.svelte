<!-- A DailyMed label or pill photo with a quiet placeholder while loading or when missing. -->
<script lang="ts">
	interface Props {
		src: string | null | undefined;
		alt: string;
		width?: number;
		height?: number;
		caption?: string;
	}

	let { src, alt, width = 120, height = 120, caption }: Props = $props();
	let status: 'loading' | 'loaded' | 'failed' = $state('loading');
	let img: HTMLImageElement | undefined = $state();

	$effect(() => {
		// The image may finish before hydration; read its state once mounted.
		if (img?.complete) status = img.naturalWidth > 0 ? 'loaded' : 'failed';
	});
</script>

<figure class="photo" style:width="{width}px" style:height="{height}px">
	{#if src && status !== 'failed'}
		<img
			bind:this={img}
			{src}
			{alt}
			loading="lazy"
			decoding="async"
			referrerpolicy="no-referrer"
			class:visible={status === 'loaded'}
			onload={() => (status = 'loaded')}
			onerror={() => (status = 'failed')}
		/>
		{#if status === 'loading'}<span class="shimmer" aria-hidden="true"></span>{/if}
	{:else}
		<span class="empty">
			<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
				<path
					d="M4 6h16v12H4z M4 15l4-4 4 4 3-3 5 5"
					fill="none"
					stroke="currentColor"
					stroke-width="1.6"
					stroke-linejoin="round"
				/>
			</svg>
			No photo
		</span>
	{/if}
	{#if caption}<figcaption>{caption}</figcaption>{/if}
</figure>

<style>
	.photo {
		position: relative;
		margin: 0;
		flex: none;
		border-radius: var(--radius-sm);
		overflow: hidden;
		background: var(--surface-2);
		border: 1px solid var(--line);
	}
	img {
		width: 100%;
		height: 100%;
		object-fit: contain;
		background: #fff;
		opacity: 0;
		transition: opacity 0.25s;
	}
	img.visible {
		opacity: 1;
	}
	.shimmer {
		position: absolute;
		inset: 0;
		background: linear-gradient(
			100deg,
			transparent 30%,
			rgb(255 255 255 / 45%) 50%,
			transparent 70%
		);
		background-size: 200% 100%;
		animation: shimmer 1.2s infinite;
	}
	@keyframes shimmer {
		from {
			background-position: 200% 0;
		}
		to {
			background-position: -200% 0;
		}
	}
	.empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.2rem;
		height: 100%;
		color: var(--muted);
		font-size: 0.72rem;
		font-weight: 600;
	}
	figcaption {
		position: absolute;
		left: 0.35rem;
		bottom: 0.35rem;
		padding: 0.05rem 0.4rem;
		border-radius: 999px;
		background: rgb(0 0 0 / 55%);
		color: #fff;
		font-size: 0.65rem;
		font-weight: 600;
	}
</style>

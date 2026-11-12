<script lang="ts">
	let { size = 30 }: { size?: number } = $props();
	const uid = $props.id();
</script>

<span class="logo">
	<svg viewBox="0 0 64 64" width={size} height={size} aria-hidden="true">
		<defs>
			<clipPath id="{uid}-c"><rect x="5" y="19" width="54" height="26" rx="13" /></clipPath>
			<linearGradient id="{uid}-g" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0" stop-color="#fff" stop-opacity=".55" />
				<stop offset=".5" stop-color="#fff" stop-opacity="0" />
			</linearGradient>
		</defs>
		<g transform="rotate(-38 32 32)">
			<g clip-path="url(#{uid}-c)">
				<rect x="5" y="19" width="54" height="26" fill="#F6F4EE" />
				<rect x="32" y="19" width="27" height="26" fill="#0E7A64" />
				<rect x="5" y="19" width="54" height="26" fill="url(#{uid}-g)" />
			</g>
			<rect
				x="5"
				y="19"
				width="54"
				height="26"
				rx="13"
				fill="none"
				stroke="#0B5E4D"
				stroke-width="2.5"
			/>
			<line x1="32" y1="19" x2="32" y2="45" stroke="#0B5E4D" stroke-width="2.5" />
		</g>
	</svg>
	<span class="word">Pillmark</span>
</span>

<style>
	.logo {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
	}
	.word {
		font-weight: 800;
		font-size: 1.2rem;
		letter-spacing: -0.03em;
		color: var(--ink);
	}
</style>

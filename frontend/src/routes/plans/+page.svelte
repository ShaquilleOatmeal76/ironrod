<script>
	import { api, chapterHref, today as todayStr } from '#lib/api.js';
	import { reader, progress, refreshProgress } from '#lib/reader.svelte.js';

	let plans = $state(/** @type {any[]} */ ([]));
	let stats = $state(/** @type {any} */ (null));
	let loading = $state(true);

	$effect(() => {
		reader.current = null;
		reader.verse = null;
	});

	async function load() {
		[plans, stats] = await Promise.all([api.plans(), api.stats()]);
		loading = false;
		refreshProgress();
	}
	load();

	// Today's checklist: every plan's items, deduped by chapter.
	const todayItems = $derived.by(() => {
		const seen = new Map();
		for (const p of plans)
			for (const it of p.today) if (!seen.has(it.chapter_id)) seen.set(it.chapter_id, { ...it, plan: p.title });
		return [...seen.values()];
	});
	const doneCount = $derived(todayItems.filter((i) => i.done).length);
	const frac = $derived(todayItems.length ? doneCount / todayItems.length : 0);
	const CIRC = 2 * Math.PI * 66;

	async function toggle(it) {
		it.done = !it.done;
		await api.markRead(it.volume, it.book, it.chapter, it.done);
		load();
	}

	// --- new plan ---
	let showNew = $state(false);
	let kind = $state('range');
	let what = $state('bofm');
	let fromRef = $state('');
	let toRef = $state('');
	let start = $state(todayStr());
	let end = $state(todayStr(new Date(Date.now() + 1000 * 60 * 60 * 24 * 120)));
	let days = $state([true, true, true, true, true, true, false]);
	let cfmYear = $state(new Date().getFullYear());
	let title = $state('');
	let preview = $state(/** @type {any} */ (null));
	let formError = $state('');

	const body = $derived({
		kind,
		title: title.trim() || null,
		volume: kind === 'range' && what !== 'custom' ? what : null,
		from_ref: what === 'custom' ? fromRef : null,
		to_ref: what === 'custom' ? toRef : null,
		start_date: start,
		end_date: kind === 'range' ? end : null,
		days: days.map((d) => (d ? '1' : '0')).join(''),
		cfm_year: kind === 'cfm' ? Number(cfmYear) : null
	});

	let pt;
	$effect(() => {
		const b = body;
		clearTimeout(pt);
		if (!showNew) return;
		pt = setTimeout(async () => {
			try {
				preview = await api.previewPlan(b);
				formError = '';
			} catch (e) {
				preview = null;
				formError = (b.kind === 'range' && what === 'custom' && !(fromRef && toRef)) ? '' : e.message;
			}
		}, 250);
	});

	async function create(e) {
		e.preventDefault();
		try {
			await api.createPlan(body);
			showNew = false;
			title = '';
			load();
		} catch (err) {
			formError = err.message;
		}
	}

	async function archive(p) {
		if (!confirm(`Stop tracking "${p.title}"? Your reading history stays.`)) return;
		await api.archivePlan(p.id);
		load();
	}

	// --- goals ---
	const GOAL_KINDS = [
		['study_days', 'Study days / week', 7],
		['chapters', 'Chapters / week', 100],
		['notes', 'Notes / week', 50]
	];
	let editingGoals = $state(false);
	let goalDraft = $state(/** @type {Record<string, number>} */ ({}));
	function editGoals() {
		goalDraft = Object.fromEntries(GOAL_KINDS.map(([k]) => [k, stats?.goals.find((g) => g.kind === k)?.target ?? 0]));
		editingGoals = true;
	}
	async function saveGoals() {
		await Promise.all(GOAL_KINDS.map(([k]) => api.setGoal(k, Number(goalDraft[k]) || 0)));
		editingGoals = false;
		load();
	}

	// --- heatmap: 26 weeks x 7 days, Monday first ---
	const heat = $derived.by(() => {
		if (!stats) return [];
		const startD = new Date(stats.heat_since + 'T00:00:00');
		const t = todayStr();
		const cols = [];
		for (let w = 0; w < 27; w++) {
			const col = [];
			for (let d = 0; d < 7; d++) {
				const x = new Date(startD);
				x.setDate(startD.getDate() + w * 7 + d);
				const key = todayStr(x);
				col.push({ key, n: stats.heatmap[key] ?? 0, future: key > t });
			}
			cols.push(col);
		}
		return cols;
	});
	const level = (n) => (n === 0 ? 0 : n === 1 ? 1 : n <= 3 ? 2 : n <= 6 ? 3 : 4);
	const DAYNAMES = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
</script>

<svelte:head><title>Plans · Iron Rod</title></svelte:head>

<div class="wrap">
	<header class="top">
		<h1>Plans</h1>
		<span class="grow"></span>
		<button class="primary" onclick={() => (showNew = !showNew)}>{showNew ? 'Cancel' : '+ New plan'}</button>
	</header>

	<section class="today" aria-labelledby="today-h">
		<div class="card list">
			<div class="row-h"><h2 id="today-h">Today</h2><span class="mono faint">{new Date().toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' }).toLowerCase()}</span></div>
			{#if loading}
				<p class="faint mono">loading…</p>
			{:else if !plans.length}
				<p class="faint">No plans yet. Start one to get a daily reading list.</p>
			{:else if !todayItems.length}
				<p class="faint">{plans.every((p) => p.rest_day) ? 'Rest day — nothing scheduled.' : 'Nothing left for today.'}</p>
			{/if}
			{#each todayItems as it (it.chapter_id)}
				<div class="item" class:done={it.done}>
					<button class="check" aria-pressed={it.done} aria-label="{it.done ? 'Mark unread' : 'Mark read'}: {it.label}" onclick={() => toggle(it)}>{it.done ? '✓' : ''}</button>
					<span class="what"><span class="t">{it.label}</span><span class="mono p">{it.plan.toLowerCase()}</span></span>
					<a class="open mono" href={chapterHref(it.volume, it.book, it.chapter)}>open ↵</a>
				</div>
			{/each}
		</div>
		<div class="card ring">
			<svg width="150" height="150" viewBox="0 0 160 160" role="img" aria-label="Today: {doneCount} of {todayItems.length} done">
				<circle cx="80" cy="80" r="66" fill="none" stroke="var(--border)" stroke-width="12" />
				<circle cx="80" cy="80" r="66" fill="none" stroke="var(--accent)" stroke-width="12" stroke-linecap="round" stroke-dasharray="{CIRC * frac} {CIRC}" transform="rotate(-90 80 80)" />
				<text x="80" y="80" text-anchor="middle" font-family="JetBrains Mono Variable, monospace" font-size="28" font-weight="600" fill="var(--text)">{Math.round(frac * 100)}%</text>
				<text x="80" y="102" text-anchor="middle" font-family="JetBrains Mono Variable, monospace" font-size="11" fill="var(--text-faint)">today</text>
			</svg>
			<div class="mono stat"><span class="big">{stats?.streak ?? 0}</span> day streak</div>
			<div class="mono faint small">{stats?.chapters_all_time ?? 0} chapters read all-time</div>
		</div>
	</section>

	{#if showNew}
		<section class="card new" aria-labelledby="new-h">
			<h2 id="new-h">New plan</h2>
			<form onsubmit={create}>
				<div class="kinds" role="radiogroup" aria-label="Plan type">
					<button type="button" role="radio" aria-checked={kind === 'range'} class:on={kind === 'range'} onclick={() => (kind = 'range')}>Read by a date</button>
					<button type="button" role="radio" aria-checked={kind === 'cfm'} class:on={kind === 'cfm'} onclick={() => (kind = 'cfm')}>Follow Come Follow Me</button>
				</div>
				{#if kind === 'range'}
					<div class="grid">
						<label>WHAT
							<select bind:value={what}>
								<option value="bofm">Book of Mormon</option><option value="nt">New Testament</option><option value="ot">Old Testament</option>
								<option value="dc-testament">Doctrine and Covenants</option><option value="pgp">Pearl of Great Price</option><option value="custom">Custom range…</option>
							</select>
						</label>
						{#if what === 'custom'}
							<label>FROM<input bind:value={fromRef} placeholder="1 Nephi 1" /></label>
							<label>TO<input bind:value={toRef} placeholder="Moroni 10" /></label>
						{/if}
						<label>START<input type="date" bind:value={start} /></label>
						<label>FINISH BY<input type="date" bind:value={end} /></label>
					</div>
					<fieldset class="days"><legend class="mono">READING DAYS</legend>
						{#each DAYNAMES as d, i}<label class="day" class:on={days[i]}><input type="checkbox" bind:checked={days[i]} /><span class="mono">{d}</span></label>{/each}
					</fieldset>
				{:else}
					<div class="grid">
						<label>YEAR<select bind:value={cfmYear}>{#each [new Date().getFullYear() + 1, new Date().getFullYear(), new Date().getFullYear() - 1] as y}<option value={y}>{y}</option>{/each}</select></label>
						<label>START<input type="date" bind:value={start} /></label>
					</div>
				{/if}
				<label class="wide">NAME (optional)<input bind:value={title} placeholder={kind === 'cfm' ? `Come Follow Me ${cfmYear}` : 'e.g. Book of Mormon by Easter'} /></label>
				<div class="foot">
					<span class="mono summary">
						{#if preview && kind === 'range'}→ {preview.chapters} chapters · {preview.days} reading days · <span class="acc">≈ {preview.per_day} ch/day</span>
						{:else if preview && kind === 'cfm'}→ {preview.lessons ? `${preview.lessons} weekly lessons` : `import Come Follow Me ${cfmYear} in the library first`}{/if}
					</span>
					<button class="primary">Create plan</button>
				</div>
				{#if formError}<p class="err" role="alert">{formError}</p>{/if}
			</form>
		</section>
	{/if}

	{#if plans.length}
		<section aria-labelledby="ap-h">
			<h2 id="ap-h" class="label mono">ACTIVE PLANS</h2>
			<div class="cards">
				{#each plans as p (p.id)}
					<article class="card plan">
						<div class="row-h">
							<h3>{p.title}</h3>
							<span class="badge mono" class:warn={p.behind}>{p.status}</span>
						</div>
						<div class="bar"><div class:warn={p.behind} style="width:{p.total ? (100 * p.done) / p.total : 0}%"></div></div>
						<div class="mono meta"><span>{p.kind === 'cfm' ? `${p.done} / ${p.total} weeks` : `${p.done} / ${p.total} chapters`}</span><span>{p.total ? Math.round((100 * p.done) / p.total) : 0}%</span></div>
						{#if p.pace}<div class="mono pace">{p.pace}</div>{/if}
						{#if p.week}<a class="mono small" href="/doc/{p.week.doc_id}">this week's lesson →</a>{/if}
						{#if p.needs_import}<a class="mono small" href="/library">import it in the library →</a>{/if}
						<button class="mini mono" onclick={() => archive(p)}>stop tracking</button>
					</article>
				{/each}
			</div>
		</section>
	{/if}

	<section aria-labelledby="g-h">
		<div class="row-h"><h2 id="g-h" class="label mono">THIS WEEK</h2>
			<button class="mini mono" onclick={() => (editingGoals ? saveGoals() : editGoals())}>{editingGoals ? 'save goals' : 'set goals'}</button></div>
		{#if editingGoals}
			<div class="card goal-edit">
				{#each GOAL_KINDS as [k, label, max]}
					<label>{String(label).toUpperCase()}<input type="number" min="0" {max} bind:value={goalDraft[k]} /></label>
				{/each}
				<p class="faint small">0 turns a goal off.</p>
			</div>
		{/if}
		<div class="cards">
			{#if stats}
				<article class="card">
					<div class="row-h"><h3>Days studied</h3><span class="mono acc">{stats.totals.study_days} / 7</span></div>
					<div class="week">
						{#each stats.week as d}
							<div class="d"><span class="box" class:on={d.active} class:future={d.future} title="{d.chapters} ch, {d.notes} notes"></span><span class="mono">{d.label}</span></div>
						{/each}
					</div>
				</article>
				{#each stats.goals as g}
					<article class="card">
						<div class="row-h"><h3>{g.title}</h3><span class="mono" class:acc={g.value >= g.target}>{g.value} / {g.target}</span></div>
						<div class="bar"><div style="width:{Math.min(100, (100 * g.value) / g.target)}%"></div></div>
						<div class="mono faint small">{g.value >= g.target ? 'goal met ✓' : `${g.target - g.value} to go`}</div>
					</article>
				{/each}
			{/if}
		</div>
	</section>

	{#if stats}
		<section aria-labelledby="h-h">
			<h2 id="h-h" class="label mono">LAST 6 MONTHS</h2>
			<div class="card heat" role="img" aria-label="Chapters read per day over the last six months">
				{#each heat as col}
					<div class="col">{#each col as c}<span class="cell l{level(c.n)}" class:future={c.future} title="{c.key}: {c.n} chapters"></span>{/each}</div>
				{/each}
			</div>
		</section>
	{/if}
</div>

<style>
	.wrap { max-width: 1100px; margin: 0 auto; padding: 32px 24px 80px; display: flex; flex-direction: column; gap: 24px; }
	.top { display: flex; align-items: center; gap: 12px; }
	h1 { margin: 0; font-family: var(--font-scripture); font-weight: 600; font-size: 36px; }
	h2 { margin: 0; font-size: 19px; font-weight: 600; }
	h3 { margin: 0; font-size: 15px; font-weight: 600; }
	.label { font-size: 12px; letter-spacing: 0.12em; color: var(--text-faint); font-weight: 500; margin-bottom: 12px; }
	.grow { flex: 1; }
	.faint { color: var(--text-faint); }
	.small { font-size: 12px; }
	.acc { color: var(--accent); }
	.card { background: var(--bg-raised); border: 1px solid var(--border); border-radius: 10px; padding: 20px; }
	.row-h { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; margin-bottom: 12px; }
	.primary { height: 40px; padding: 0 16px; border: 0; border-radius: var(--radius); background: var(--accent); color: var(--accent-ink); font-weight: 600; cursor: pointer; }
	.today { display: flex; flex-wrap: wrap; gap: 16px; }
	.list { flex: 2 1 460px; display: flex; flex-direction: column; gap: 8px; }
	.ring { flex: 1 1 240px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; }
	.stat { font-size: 13px; color: var(--text-muted); }
	.big { font-size: 20px; color: var(--accent); font-weight: 600; }
	.item { display: flex; align-items: center; gap: 14px; padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); }
	.check { width: 30px; height: 30px; border-radius: 6px; border: 1.5px solid #3a4452; background: transparent; color: var(--accent-ink); font-weight: 700; cursor: pointer; flex: 0 0 auto; }
	.item.done .check { background: var(--accent); border-color: var(--accent); }
	.what { flex: 1; min-width: 0; display: flex; flex-direction: column; }
	.what .t { font-family: var(--font-scripture); font-size: 18px; }
	.item.done .t { color: var(--text-faint); text-decoration: line-through; }
	.what .p { font-size: 11px; color: var(--text-faint); }
	.open { font-size: 12px; text-decoration: none; border: 1px solid var(--border-strong); border-radius: 4px; padding: 6px 10px; color: var(--text-muted); }
	.new form { display: flex; flex-direction: column; gap: 14px; margin-top: 14px; }
	.kinds { display: flex; flex-wrap: wrap; gap: 6px; }
	.kinds button { height: 36px; padding: 0 12px; border-radius: var(--radius); border: 1px solid var(--border); background: none; color: var(--text-muted); cursor: pointer; }
	.kinds button.on { border-color: var(--accent-line); background: var(--accent-dim); color: var(--accent); }
	.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; }
	label { display: flex; flex-direction: column; gap: 6px; font: 11px var(--font-mono); letter-spacing: 0.08em; color: var(--text-faint); }
	label.wide { max-width: 420px; }
	input, select { height: 42px; background: var(--surface); border: 1px solid var(--border-strong); border-radius: var(--radius); color: var(--text); font: 14px var(--font-ui); padding: 0 10px; letter-spacing: 0; }
	.days { border: 0; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 6px; }
	.days legend { font-size: 11px; letter-spacing: 0.08em; color: var(--text-faint); margin-bottom: 6px; }
	.day { flex-direction: row; }
	.day input { position: absolute; opacity: 0; width: 1px; height: 1px; }
	.day span { width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 6px; border: 1px solid var(--border-strong); color: var(--text-muted); font-size: 13px; cursor: pointer; }
	.day.on span { background: var(--accent-dim); border-color: var(--accent-line); color: var(--accent); }
	.day input:focus-visible + span { outline: 2px solid var(--accent); }
	.foot { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px; padding-top: 14px; border-top: 1px solid var(--border); }
	.summary { font-size: 13px; color: var(--text-muted); }
	.err { margin: 0; color: var(--hl-promise); font-size: 13px; }
	.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
	.plan { display: flex; flex-direction: column; gap: 10px; }
	.plan .row-h { margin-bottom: 0; }
	.badge { font-size: 11px; color: var(--accent); border: 1px solid var(--accent-line); border-radius: 4px; padding: 2px 8px; white-space: nowrap; }
	.badge.warn { color: var(--hl-promise); border-color: #4a3a1e; }
	.bar { height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; }
	.bar div { height: 100%; background: var(--accent); }
	.bar div.warn { background: var(--hl-promise); }
	.meta { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-faint); }
	.pace { font-size: 12px; color: var(--text-muted); }
	.mini { align-self: flex-start; border: 0; background: none; color: var(--text-faint); font-size: 11px; padding: 4px 0; cursor: pointer; }
	.mini:hover { color: var(--text); }
	.goal-edit { display: flex; flex-wrap: wrap; gap: 14px; align-items: flex-end; margin-bottom: 14px; }
	.goal-edit input { width: 120px; }
	.week { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 6px; }
	.d { display: flex; flex-direction: column; align-items: center; gap: 6px; font-size: 11px; color: var(--text-faint); }
	.box { width: 100%; height: 28px; border-radius: 4px; border: 1px solid var(--border); background: var(--bg); }
	.box.on { background: var(--accent); border-color: var(--accent); }
	.box.future { border-style: dashed; }
	.heat { display: flex; gap: 3px; overflow-x: auto; padding: 16px; }
	.col { display: flex; flex-direction: column; gap: 3px; }
	.cell { width: 13px; height: 13px; border-radius: 2px; background: #151a21; }
	.cell.l1 { background: color-mix(in srgb, var(--accent) 30%, #151a21); }
	.cell.l2 { background: color-mix(in srgb, var(--accent) 55%, #151a21); }
	.cell.l3 { background: color-mix(in srgb, var(--accent) 78%, #151a21); }
	.cell.l4 { background: var(--accent); }
	.cell.future { opacity: 0.25; }
</style>

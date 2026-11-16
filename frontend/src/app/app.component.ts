import { AfterViewInit, Component, ElementRef, NgZone, OnDestroy, ViewChild, inject, signal } from '@angular/core';
import Globe, { type GlobeInstance } from 'globe.gl';
import type { Feature, FeatureCollection, Geometry, Point } from 'geojson';

type SourceId = 'ign' | 'usgs' | 'emsc';
type Properties = {
  mag: number | null; place: string; time: number; updated: number;
  country_name?: string | null; country_id?: string | null; source?: SourceId | string | null;
};
type Events = FeatureCollection<Point, Properties> & {
  metadata?: {
    generated?: number; mode?: string; last_ingestion?: number | null; count?: number;
    truncated?: boolean; limit?: number; offset?: number; source?: string; url?: string;
  };
};
type Config = {
  mode: 'demo' | 'api'; apiUrl: string; refreshMs: number; skipNgrokWarning: boolean;
};
type CountryOption = { country_id: string; name_es: string; subregion: string | null };
type Bucket = { etiqueta: string; total: number };
type Stats = {
  periodo: { start: string; end: string; unidad: string };
  filtros: { min_mag: number | null; country_id: string | null; subregion: string | null };
  total: number;
  sin_valor: { magnitud: number; profundidad: number; pais: number };
  ventanas: { inicio: string; fin: string; total: number }[];
  por_pais: { country_id: string | null; nombre: string; total: number }[];
  magnitud: { nulos: number; denominador: number; media: number | null; tramos: Bucket[] };
  profundidad: { nulos: number; denominador: number; media: number | null; unidad: string; tramos: Bucket[] };
  comparacion: {
    reciente: { inicio: string; fin: string; total: number; etiqueta: string };
    historico: { anio: number; dias: number; total: number; media_diaria: number };
    corte_magnitud: number;
    corte_forzado_a_4: boolean;
    country_id: string | null;
    subregion: string | null;
    variacion_porcentual: number | null;
    aviso: string;
  };
};
type TableRow = { id: string; time: string; mag: string; depth: string; country: string; place: string; source: string };
type QuakePoint = {
  lat: number;
  lng: number;
  /** Radio base en grados; se escala con el zoom de la cámara. */
  baseRadius: number;
  color: string;
  place: string;
  mag: string;
  depth: string;
  time: string;
  country: string;
  source: string;
  id: string;
  label: string;
};

const SOURCE_LABEL: Record<SourceId, string> = { ign: 'IGN', usgs: 'USGS', emsc: 'EMSC' };
const EARTH_NIGHT = 'https://cdn.jsdelivr.net/npm/three-globe/example/img/earth-night.jpg';
const EARTH_TOPO = 'https://cdn.jsdelivr.net/npm/three-globe/example/img/earth-topology.png';
const NIGHT_SKY = 'https://cdn.jsdelivr.net/npm/three-globe/example/img/night-sky.png';
/** Helvetiker no tiene ñ/tildes; optimer sí (Latin Extended). */
const LABEL_TYPEFACE = 'https://cdn.jsdelivr.net/npm/three@0.180.0/examples/fonts/optimer_regular.typeface.json';
const CACHE_KEY = 'observatorio-sismico-cache-v1';
const CACHE_MAX_FEATURES = 800;

type CountryLabel = { lat: number; lng: number; name: string };

/** Centroide aproximado del anillo exterior (para etiquetas siempre visibles). */
function ringCentroid(ring: number[][]): { lat: number; lng: number; area: number } | null {
  if (!ring || ring.length < 3) return null;
  let area = 0;
  let cx = 0;
  let cy = 0;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [x0, y0] = ring[j];
    const [x1, y1] = ring[i];
    if (![x0, y0, x1, y1].every(Number.isFinite)) continue;
    const cross = x0 * y1 - x1 * y0;
    area += cross;
    cx += (x0 + x1) * cross;
    cy += (y0 + y1) * cross;
  }
  if (Math.abs(area) < 1e-12) {
    const lon = ring.reduce((s, p) => s + p[0], 0) / ring.length;
    const lat = ring.reduce((s, p) => s + p[1], 0) / ring.length;
    return Number.isFinite(lon) && Number.isFinite(lat) ? { lat, lng: lon, area: 0 } : null;
  }
  area *= 0.5;
  return { lng: cx / (6 * area), lat: cy / (6 * area), area: Math.abs(area) };
}

function featureLabelPoint(geometry: Geometry): { lat: number; lng: number } | null {
  const rings: number[][][] = [];
  if (geometry.type === 'Polygon') rings.push(geometry.coordinates[0]);
  else if (geometry.type === 'MultiPolygon') {
    for (const poly of geometry.coordinates) rings.push(poly[0]);
  } else return null;
  let best: { lat: number; lng: number; area: number } | null = null;
  for (const ring of rings) {
    const c = ringCentroid(ring);
    if (!c) continue;
    if (!best || c.area > best.area) best = c;
  }
  return best ? { lat: best.lat, lng: best.lng } : null;
}

type SourceCache = {
  version: 1;
  savedAt: number;
  sources: Partial<Record<SourceId, Events>>;
  stats?: Stats | null;
};

@Component({
  selector: 'app-root', standalone: true, imports: [],
  templateUrl: './app.component.html', styleUrl: './app.component.css'
})
export class AppComponent implements AfterViewInit, OnDestroy {
  @ViewChild('globeHost', { static: true }) private globeHost!: ElementRef<HTMLDivElement>;
  private readonly zone = inject(NgZone);

  readonly mode = signal('Cargando configuración');
  readonly status = signal('Preparando el globo…');
  readonly lastRead = signal('Sin lectura');
  readonly generated = signal('Sin información');
  readonly ingestion = signal('Sin información');
  readonly ingestionWarning = signal('');
  readonly count = signal(0);
  readonly omitted = signal(0);
  readonly countriesStatus = signal('Cargando catálogo');
  readonly filterStart = signal('');
  readonly filterEnd = signal('');
  readonly filterMag = signal('');
  readonly filterCountry = signal('');
  readonly filterRegion = signal('');
  readonly sourceIgn = signal(true);
  readonly sourceUsgs = signal(true);
  readonly sourceEmsc = signal(true);
  readonly sourceStatus = signal('');
  readonly countries = signal<CountryOption[]>([]);
  readonly stats = signal<Stats | null>(null);
  readonly tableRows = signal<TableRow[]>([]);
  readonly truncated = signal(false);
  readonly resultCount = signal(0);
  readonly offset = signal(0);
  readonly reproduction = signal(false);
  readonly selected = signal<QuakePoint | null>(null);
  readonly autoRotate = signal(true);
  readonly cacheNotice = signal('');

  private globe?: GlobeInstance;
  private timer?: ReturnType<typeof setTimeout>;
  private resumeRotateTimer?: ReturnType<typeof setTimeout>;
  private controller = new AbortController();
  private destroyed = false;
  private activeConfig?: Config;
  private resizeObserver?: ResizeObserver;
  /** 1 = alejados; al acercar baja hasta un piso alto para seguir pudiendo clicar. */
  private radiusScale = 1;
  private radiusRaf = 0;
  private readonly onControlsChange = (): void => this.scheduleRadiusScale();

  async ngAfterViewInit(): Promise<void> {
    this.initGlobe();
    await this.loadCountryBorders();
    try {
      const config = await this.readJson<Config>('config.json');
      if (!['demo', 'api'].includes(config.mode)) throw new Error('Modo inválido');
      this.activeConfig = config;
      this.mode.set(config.mode === 'demo' ? 'DEMOSTRACIÓN · datos ficticios' : 'API · datos del backend y fuentes públicas');
      if (config.mode === 'api') {
        const headers: Record<string, string> = {};
        if (config.skipNgrokWarning) headers['ngrok-skip-browser-warning'] = '1';
        try {
          this.countries.set(await this.readJson<CountryOption[]>(`${config.apiUrl.replace(/\/$/, '')}/api/paises`, headers));
          this.countriesStatus.set('Fronteras en el globo · catálogo de filtros cargado');
        } catch {
          this.countries.set([]);
          this.countriesStatus.set('Fronteras en el globo · catálogo de filtros no disponible');
        }
      } else {
        this.countriesStatus.set('Fronteras en el globo · modo demo');
      }
      await this.refresh(config);
    } catch {
      this.status.set('Error: revisa public/config.json');
    }
  }

  /** Contornos Natural Earth 1:110m + nombres siempre visibles (sin hover). */
  private async loadCountryBorders(): Promise<void> {
    if (!this.globe) return;
    try {
      const [collection, typeface] = await Promise.all([
        this.readJson<FeatureCollection<Geometry, { NAME_ES?: string; ADMIN?: string }>>('datos/paises.geojson'),
        this.readJson<object>(LABEL_TYPEFACE),
      ]);
      const features = (collection.features ?? []).filter(
        (feature): feature is Feature<Geometry, { NAME_ES?: string; ADMIN?: string }> =>
          Boolean(feature?.geometry) && (feature.geometry.type === 'Polygon' || feature.geometry.type === 'MultiPolygon')
      );
      const labels: CountryLabel[] = [];
      for (const feature of features) {
        const name = feature.properties?.NAME_ES ?? feature.properties?.ADMIN;
        if (!name) continue;
        const point = featureLabelPoint(feature.geometry);
        if (!point) continue;
        labels.push({ ...point, name });
      }
      this.globe
        .polygonsData(features)
        .polygonGeoJsonGeometry('geometry')
        .polygonCapColor(() => 'rgba(0, 0, 0, 0)')
        .polygonSideColor(() => 'rgba(0, 0, 0, 0)')
        .polygonStrokeColor(() => 'rgba(186, 210, 230, 0.72)')
        .polygonAltitude(0.004)
        .polygonCapCurvatureResolution(4)
        .polygonsTransitionDuration(0)
        .labelsData(labels)
        .labelLat('lat')
        .labelLng('lng')
        .labelText('name')
        .labelTypeFace(typeface)
        .labelColor(() => 'rgba(226, 236, 248, 0.92)')
        .labelSize(0.35)
        .labelDotRadius(0)
        .labelAltitude(0.012)
        .labelResolution(3)
        .labelsTransitionDuration(0);
    } catch {
      this.countriesStatus.set('No se pudieron cargar las fronteras del globo');
    }
  }

  private initGlobe(): void {
    const host = this.globeHost.nativeElement;
    this.globe = new Globe(host, { animateIn: true })
      .globeImageUrl(EARTH_NIGHT)
      .bumpImageUrl(EARTH_TOPO)
      .backgroundImageUrl(NIGHT_SKY)
      .showAtmosphere(true)
      .atmosphereColor('#4f8cff')
      .atmosphereAltitude(0.18)
      .pointsData([])
      .pointLat('lat')
      .pointLng('lng')
      // Por encima de fronteras (0.004) y etiquetas (0.012) para que el clic no lo robe el polígono.
      .pointAltitude(0.015)
      .pointRadius((d: object) => (d as QuakePoint).baseRadius * this.radiusScale)
      .pointColor('color')
      .pointLabel('label')
      .pointsMerge(false)
      .pointsTransitionDuration(0)
      .ringsData([])
      .ringLat('lat')
      .ringLng('lng')
      .ringColor((d: object) => (d as QuakePoint).color)
      .ringMaxRadius(() => 0.55 + this.radiusScale * 2.25)
      .ringPropagationSpeed(1.4)
      .ringRepeatPeriod(1400)
      .onPointClick((point) => {
        this.zone.run(() => {
          this.pauseAutoRotate();
          this.selected.set(point as QuakePoint);
        });
      })
      .onGlobeClick(() => this.zone.run(() => this.selected.set(null)));

    const controls = this.globe.controls();
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.45;
    controls.enableDamping = true;
    controls.minDistance = 120;
    controls.maxDistance = 500;
    controls.addEventListener('change', this.onControlsChange);
    this.applyRadiusScale();

    const pause = (): void => this.zone.run(() => this.pauseAutoRotate());
    host.addEventListener('pointerdown', pause);
    host.addEventListener('wheel', pause, { passive: true });
    host.addEventListener('touchstart', pause, { passive: true });

    this.zone.runOutsideAngular(() => {
      this.resizeGlobe();
      this.resizeObserver = new ResizeObserver(() => this.resizeGlobe());
      this.resizeObserver.observe(host);
    });
  }

  private scheduleRadiusScale(): void {
    if (this.radiusRaf || this.destroyed) return;
    this.radiusRaf = requestAnimationFrame(() => {
      this.radiusRaf = 0;
      this.applyRadiusScale();
    });
  }

  /** Acercar cámara → ligeramente más pequeños; alejar → tamaño completo. Piso alto para clicar. */
  private applyRadiusScale(): void {
    if (!this.globe || this.destroyed) return;
    const controls = this.globe.controls();
    const min = controls.minDistance;
    const max = controls.maxDistance;
    const distance = controls.getDistance();
    const t = Math.min(1, Math.max(0, (distance - min) / Math.max(1, max - min)));
    // Zoom máximo (cerca): 60 % del radio base; zoom mínimo (lejos): 100 %.
    this.radiusScale = 0.6 + t * 0.4;
    // Reaplicar accessors para que three-globe regenere la geometría.
    this.globe
      .pointRadius((d: object) => (d as QuakePoint).baseRadius * this.radiusScale)
      .ringMaxRadius(0.55 + this.radiusScale * 2.25);
  }

  private resizeGlobe(): void {
    if (!this.globe || this.destroyed) return;
    const host = this.globeHost.nativeElement;
    const width = Math.max(320, host.clientWidth);
    const height = Math.max(360, host.clientHeight);
    this.globe.width(width).height(height);
  }

  private pauseAutoRotate(): void {
    if (!this.globe) return;
    const controls = this.globe.controls();
    controls.autoRotate = false;
    this.autoRotate.set(false);
    clearTimeout(this.resumeRotateTimer);
    this.resumeRotateTimer = setTimeout(() => {
      if (this.destroyed || !this.globe) return;
      this.globe.controls().autoRotate = true;
      this.autoRotate.set(true);
    }, 8000);
  }

  toggleAutoRotate(): void {
    if (!this.globe) return;
    const next = !this.globe.controls().autoRotate;
    this.globe.controls().autoRotate = next;
    this.autoRotate.set(next);
    clearTimeout(this.resumeRotateTimer);
  }

  clearSelection(): void {
    this.selected.set(null);
  }

  private async readJson<T>(url: string, headers: Record<string, string> = {}): Promise<T> {
    const response = await fetch(url, {
      headers, cache: 'no-store',
      signal: AbortSignal.any([this.controller.signal, AbortSignal.timeout(20000)])
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json() as Promise<T>;
  }

  selectedSources(): SourceId[] {
    const selected: SourceId[] = [];
    if (this.sourceIgn()) selected.push('ign');
    if (this.sourceUsgs()) selected.push('usgs');
    if (this.sourceEmsc()) selected.push('emsc');
    return selected;
  }

  toggleSource(source: SourceId, checked: boolean): void {
    if (source === 'ign') this.sourceIgn.set(checked);
    if (source === 'usgs') this.sourceUsgs.set(checked);
    if (source === 'emsc') this.sourceEmsc.set(checked);
    this.offset.set(0);
    if (this.activeConfig) void this.refresh(this.activeConfig);
  }

  sourceChecked(event: Event): boolean {
    return (event.target as HTMLInputElement).checked;
  }

  private async refresh(config: Config): Promise<void> {
    clearTimeout(this.timer);
    try {
      const base = config.apiUrl.replace(/\/$/, '');
      const headers: Record<string, string> = {};
      if (config.mode === 'api' && config.skipNgrokWarning) headers['ngrok-skip-browser-warning'] = '1';

      let data: Events;
      let usedCache = false;
      if (config.mode === 'demo') {
        data = await this.readJson<Events>('datos/terremotos-demo.geojson', headers);
        this.sourceStatus.set('Modo demo: el filtro de fuentes no aplica');
        this.cacheNotice.set('');
      } else if (this.reproduction()) {
        data = await this.readJson<Events>(`${base}/api/eventos${this.query(true)}`, headers);
        this.sourceStatus.set('Reproducción del pipeline: el filtro de fuentes no aplica');
        this.cacheNotice.set('');
      } else {
        const loaded = await this.loadSources(base, headers);
        data = loaded.data;
        usedCache = loaded.usedCache;
      }

      if (this.destroyed) return;
      this.paintEvents(data, usedCache);

      if (config.mode === 'api') {
        try {
          const stats = await this.readJson<Stats>(`${base}/api/estadisticas${this.query(false)}`, headers);
          this.stats.set(stats);
          if (!this.reproduction()) this.saveStatsToCache(stats);
        } catch {
          const cachedStats = this.readCache()?.stats ?? null;
          if (cachedStats) {
            this.stats.set(cachedStats);
            if (!usedCache) {
              this.status.set('Eventos actualizados; estadísticas desde la última copia local (API Docker no respondió).');
              return;
            }
          } else {
            this.stats.set(null);
            if (!this.reproduction() && !usedCache) {
              this.status.set('El globo se actualizó con las fuentes seleccionadas, pero las estadísticas del pipeline no respondieron.');
              return;
            }
          }
        }
      }
      if (usedCache) {
        this.status.set('API Docker no disponible · mostrando la última copia guardada en el navegador');
      } else {
        this.status.set(config.mode === 'demo' ? 'Ejemplo estático: no representa actividad real' : 'API accesible · consulta completada');
      }
    } catch {
      if (this.destroyed) return;
      const cached = this.eventsFromCache(this.selectedSources());
      if (cached && cached.features.length > 0) {
        this.paintEvents(cached, true);
        const cachedStats = this.readCache()?.stats ?? null;
        if (cachedStats) this.stats.set(cachedStats);
        this.sourceStatus.set('Sin respuesta de Docker · datos desde copia local');
        this.status.set('API Docker no disponible · mostrando la última copia guardada en el navegador');
      } else {
        this.status.set('No se pudo actualizar y no hay copia local. Revisa API, túnel y CORS.');
      }
    } finally {
      if (!this.destroyed && config.mode === 'api') {
        this.timer = setTimeout(() => void this.refresh(config), Math.max(30000, Number(config.refreshMs) || 60000));
      }
    }
  }

  private paintEvents(data: Events, fromCache: boolean): void {
    if (data.type !== 'FeatureCollection' || !Array.isArray(data.features)) throw new Error('Se esperaba FeatureCollection');

    const points: QuakePoint[] = [];
    const rows: TableRow[] = [];
    let omitted = 0;

    for (const feature of data.features) {
      const p = feature.properties;
      const c = feature.geometry?.type === 'Point' ? feature.geometry.coordinates : [];
      const [lon, lat, depth] = c;
      const magnitude = p && typeof p.mag === 'number' && Number.isFinite(p.mag) ? p.mag : null;
      const depthOk = typeof depth === 'number' && Number.isFinite(depth);
      const source = (p?.source as string) || 'nd';
      const fuenteTxt = SOURCE_LABEL[source as SourceId] ?? (source === 'nd' ? 'ND' : String(source).toUpperCase());
      const place = p?.place ?? 'Sin descripción';
      const country = p?.country_name ?? 'Sin país asignado';
      const time = this.date(p?.time);
      const id = String(feature.id ?? 'ND');
      const magLabel = magnitude === null ? 'ND' : String(magnitude);
      const depthLabel = depthOk ? `${depth} km` : 'ND';

      rows.push({
        id, time, mag: magLabel, depth: depthOk ? String(depth) : 'ND', country, place, source: fuenteTxt,
      });

      if (!p || !Number.isFinite(lon) || !Number.isFinite(lat) || Math.abs(lon) > 180 || Math.abs(lat) > 90) {
        omitted++;
        continue;
      }

      const color = !depthOk ? '#94a3b8' : depth < 70 ? '#f5c542' : depth < 300 ? '#ff6b3d' : '#a78bfa';
      const baseRadius = magnitude === null ? 0.55 : Math.max(0.45, Math.min(1.8, 0.45 + (magnitude + 1) * 0.16));
      points.push({
        lat, lng: lon, baseRadius, color, place,
        mag: magLabel, depth: depthLabel, time, country, source: fuenteTxt, id,
        label: `${place}\nMag ${magLabel} · ${depthLabel}`,
      });
    }

    this.applyRadiusScale();
    this.globe?.pointsData(points);
    const rings = [...points]
      .sort((a, b) => Number(b.mag === 'ND' ? -1 : b.mag) - Number(a.mag === 'ND' ? -1 : a.mag))
      .slice(0, Math.min(40, points.length));
    this.globe?.ringsData(rings);

    this.count.set(points.length);
    this.omitted.set(omitted);
    this.tableRows.set(rows);
    this.truncated.set(Boolean(data.metadata?.truncated));
    this.resultCount.set(data.metadata?.count ?? points.length);
    this.lastRead.set(fromCache ? this.cacheSavedLabel() : new Date().toISOString());
    this.generated.set(this.date(data.metadata?.generated));
    this.ingestion.set(this.date(data.metadata?.last_ingestion));
    const ingestedAt = data.metadata?.last_ingestion;
    const ingestaVieja = typeof ingestedAt === 'number' && Number.isFinite(ingestedAt) && Date.now() - ingestedAt > 5 * 60 * 1000;
    this.ingestionWarning.set(ingestaVieja ? 'El productor parece parado: la última ingesta USGS supera 5 minutos, aunque la API responda.' : '');
    this.cacheNotice.set(fromCache
      ? `Copia local del ${this.cacheSavedLabel()} (Docker apagado o sin respuesta).`
      : '');
  }

  /** Solo habla con la API Docker (`/api/fuentes/*`); guarda cada lectura OK en localStorage. */
  private async loadSources(base: string, headers: Record<string, string>): Promise<{ data: Events; usedCache: boolean }> {
    const selected = this.selectedSources();
    if (selected.length === 0) {
      this.sourceStatus.set('Ninguna fuente activa: marca IGN, USGS o EMSC');
      this.cacheNotice.set('');
      return {
        data: { type: 'FeatureCollection', metadata: { generated: Date.now(), count: 0 }, features: [] },
        usedCache: false,
      };
    }

    const live: SourceId[] = [];
    const cached: SourceId[] = [];
    const failed: string[] = [];
    const bags: { source: SourceId; data: Events }[] = [];

    await Promise.all(selected.map(async (source) => {
      const url = `${base}/api/fuentes/${source}`;
      try {
        const data = await this.readJson<Events>(url, headers);
        if (data.type !== 'FeatureCollection' || !Array.isArray(data.features)) throw new Error('formato');
        this.saveSourceToCache(source, data);
        live.push(source);
        bags.push({ source, data });
      } catch (error) {
        const fromDisk = this.readCache()?.sources?.[source];
        if (fromDisk?.features?.length) {
          cached.push(source);
          bags.push({ source, data: fromDisk });
        } else {
          failed.push(`${SOURCE_LABEL[source]} (${error instanceof Error ? error.message : 'error'})`);
        }
      }
    }));

    this.sourceStatus.set([
      live.length ? `API Docker OK: ${live.map((s) => SOURCE_LABEL[s]).join(', ')}` : '',
      cached.length ? `Copia local: ${cached.map((s) => SOURCE_LABEL[s]).join(', ')}` : '',
      failed.length ? `Sin datos: ${failed.join(', ')}` : '',
    ].filter(Boolean).join(' · ') || 'Sin lecturas');

    if (bags.length === 0) throw new Error('Ninguna fuente respondió');

    const features = bags.flatMap((item) => (item.data.features ?? []).map((feature) => {
      const properties = { ...(feature.properties ?? {}), source: feature.properties?.source ?? item.source };
      return { ...feature, properties };
    })).filter((feature) => this.passesClientFilters(feature.properties));

    return {
      data: {
        type: 'FeatureCollection',
        metadata: { generated: Date.now(), count: features.length, mode: cached.length && !live.length ? 'cache' : 'fuentes' },
        features,
      },
      usedCache: live.length === 0 && cached.length > 0,
    };
  }

  private readCache(): SourceCache | null {
    try {
      const raw = localStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw) as SourceCache;
      if (parsed?.version !== 1 || typeof parsed.savedAt !== 'number') return null;
      return parsed;
    } catch {
      return null;
    }
  }

  private writeCache(next: SourceCache): void {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify(next));
    } catch {
      // Cuota llena: recortar features y reintentar una vez.
      const trimmed: SourceCache = {
        ...next,
        sources: Object.fromEntries(
          Object.entries(next.sources).map(([key, value]) => [key, value ? this.trimEvents(value) : value])
        ) as SourceCache['sources'],
      };
      try {
        localStorage.setItem(CACHE_KEY, JSON.stringify(trimmed));
      } catch {
        /* sin espacio: se conserva lo que ya hubiera */
      }
    }
  }

  private trimEvents(data: Events): Events {
    const features = [...(data.features ?? [])]
      .sort((a, b) => (Number(b.properties?.time) || 0) - (Number(a.properties?.time) || 0))
      .slice(0, CACHE_MAX_FEATURES);
    return {
      ...data,
      features,
      metadata: { ...data.metadata, count: features.length, truncated: true },
    };
  }

  private saveSourceToCache(source: SourceId, data: Events): void {
    const slim = this.trimEvents({
      type: 'FeatureCollection',
      metadata: {
        generated: data.metadata?.generated ?? Date.now(),
        count: data.features?.length ?? 0,
        source,
        mode: data.metadata?.mode,
        last_ingestion: data.metadata?.last_ingestion ?? null,
      },
      features: data.features ?? [],
    });
    const prev = this.readCache();
    this.writeCache({
      version: 1,
      savedAt: Date.now(),
      sources: { ...(prev?.sources ?? {}), [source]: slim },
      stats: prev?.stats ?? null,
    });
  }

  private saveStatsToCache(stats: Stats): void {
    const prev = this.readCache() ?? { version: 1 as const, savedAt: Date.now(), sources: {} };
    this.writeCache({ ...prev, savedAt: prev.savedAt || Date.now(), stats });
  }

  private eventsFromCache(selected: SourceId[]): Events | null {
    const cache = this.readCache();
    if (!cache) return null;
    const bags = selected
      .map((source) => ({ source, data: cache.sources[source] }))
      .filter((item): item is { source: SourceId; data: Events } => Boolean(item.data?.features?.length));
    if (bags.length === 0) return null;
    const features = bags.flatMap((item) => (item.data.features ?? []).map((feature) => {
      const properties = { ...(feature.properties ?? {}), source: feature.properties?.source ?? item.source };
      return { ...feature, properties };
    })).filter((feature) => this.passesClientFilters(feature.properties));
    return {
      type: 'FeatureCollection',
      metadata: { generated: cache.savedAt, count: features.length, mode: 'cache' },
      features,
    };
  }

  private cacheSavedLabel(): string {
    const savedAt = this.readCache()?.savedAt;
    if (typeof savedAt !== 'number' || !Number.isFinite(savedAt)) return 'ND';
    return new Date(savedAt).toISOString();
  }

  private passesClientFilters(properties: Properties | null | undefined): boolean {
    if (!properties) return false;
    const minMag = this.filterMag() === '' ? null : Number(this.filterMag());
    if (minMag !== null && Number.isFinite(minMag)) {
      if (typeof properties.mag !== 'number' || !Number.isFinite(properties.mag) || properties.mag < minMag) return false;
    }
    const start = this.filterStart() ? Date.parse(this.asUtc(this.filterStart())) : null;
    const end = this.filterEnd() ? Date.parse(this.asUtc(this.filterEnd())) : null;
    const time = typeof properties.time === 'number' ? properties.time : null;
    if (start !== null && !Number.isNaN(start) && (time === null || time < start)) return false;
    if (end !== null && !Number.isNaN(end) && (time === null || time >= end)) return false;
    if (this.filterCountry()) {
      const wanted = this.filterCountry();
      if (wanted === 'sin-pais') {
        if (properties.country_id) return false;
      } else if (properties.country_id !== wanted) {
        return false;
      }
    }
    return true;
  }

  applyFilters(event: Event): void {
    event.preventDefault();
    this.offset.set(0);
    if (this.activeConfig) void this.refresh(this.activeConfig);
  }

  clearFilters(): void {
    this.filterStart.set(''); this.filterEnd.set(''); this.filterMag.set('');
    this.filterCountry.set(''); this.filterRegion.set('');
    this.sourceIgn.set(true); this.sourceUsgs.set(true); this.sourceEmsc.set(true);
    this.offset.set(0);
    if (this.activeConfig) void this.refresh(this.activeConfig);
  }

  changePage(direction: number): void {
    this.offset.update((value) => Math.max(0, value + direction));
    if (this.activeConfig) void this.refresh(this.activeConfig);
  }

  regions(): string[] {
    return [...new Set(this.countries().map((country) => country.subregion).filter((region): region is string => Boolean(region)))].sort();
  }

  windowBars(): { label: string; total: number }[] {
    const windows = this.stats()?.ventanas ?? [];
    if (windows.length <= 72) return windows.map((window) => ({ label: window.inicio.slice(0, 16), total: window.total }));
    const days = new Map<string, number>();
    for (const window of windows) days.set(window.inicio.slice(0, 10), (days.get(window.inicio.slice(0, 10)) ?? 0) + window.total);
    return [...days].map(([label, total]) => ({ label, total }));
  }

  countryBars(): { nombre: string; total: number }[] {
    const rows = this.stats()?.por_pais ?? [];
    const top = rows.slice(0, 12);
    const missing = rows.find((row) => row.country_id === null);
    if (missing && !top.some((row) => row.country_id === null)) top.push(missing);
    return top;
  }

  barWidth(total: number, rows: { total: number }[]): number {
    const max = rows.reduce((highest, row) => Math.max(highest, row.total), 0);
    return max === 0 ? 0 : Math.max(2, Math.round((total / max) * 100));
  }

  variation(): string {
    const value = this.stats()?.comparacion.variacion_porcentual;
    return value === null || value === undefined ? 'ND' : `${value.toFixed(1)} %`;
  }

  scopeLabel(): string {
    const stats = this.stats();
    if (!stats) return 'Mundial';
    if (stats.comparacion.country_id === 'sin-pais') return 'Sin país asignado';
    if (stats.comparacion.country_id) {
      return this.countries().find((country) => country.country_id === stats.comparacion.country_id)?.name_es ?? stats.comparacion.country_id;
    }
    return stats.comparacion.subregion ?? 'Mundial';
  }

  private query(withOffset: boolean): string {
    const params = new URLSearchParams();
    if (this.filterStart()) params.set('start', this.asUtc(this.filterStart()));
    if (this.filterEnd()) params.set('end', this.asUtc(this.filterEnd()));
    if (this.filterMag() !== '') params.set('min_mag', this.filterMag());
    if (this.filterCountry()) params.set('country_id', this.filterCountry());
    if (this.filterRegion()) params.set('subregion', this.filterRegion());
    if (this.reproduction()) params.set('mode', 'replay');
    if (withOffset && this.offset() > 0) params.set('offset', String(this.offset()));
    const text = params.toString();
    return text ? `?${text}` : '';
  }

  private asUtc(value: string): string {
    return value.length === 16 ? `${value}:00Z` : `${value}Z`;
  }

  toggleReproduction(): void {
    this.reproduction.update((value) => !value);
    this.offset.set(0);
    if (this.activeConfig) void this.refresh(this.activeConfig);
  }

  inputValue(event: Event): string {
    return (event.target as HTMLInputElement | HTMLSelectElement).value;
  }

  private date(value: unknown): string {
    if (typeof value !== 'number' || !Number.isFinite(value)) return 'ND';
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? 'ND' : d.toISOString();
  }

  ngOnDestroy(): void {
    this.destroyed = true;
    clearTimeout(this.timer);
    clearTimeout(this.resumeRotateTimer);
    cancelAnimationFrame(this.radiusRaf);
    this.globe?.controls().removeEventListener('change', this.onControlsChange);
    this.resizeObserver?.disconnect();
    this.controller.abort();
    const globe = this.globe as (GlobeInstance & { _destructor?: () => void }) | undefined;
    globe?._destructor?.();
    this.globe = undefined;
  }
}

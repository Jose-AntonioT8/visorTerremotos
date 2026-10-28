import { Component, OnDestroy, signal } from '@angular/core';
import { LeafletDirective } from '@bluehalo/ngx-leaflet';
import * as L from 'leaflet';
import type { FeatureCollection, Point } from 'geojson';

type Properties = { mag: number | null; place: string; time: number; updated: number; country_name?: string | null };
type Events = FeatureCollection<Point, Properties> & {
  metadata?: { generated?: number; mode?: string; last_ingestion?: number | null; count?: number; truncated?: boolean; limit?: number; offset?: number };
};
type Config = { mode: 'demo' | 'api'; apiUrl: string; refreshMs: number; skipNgrokWarning: boolean };
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
type TableRow = { id: string; time: string; mag: string; depth: string; country: string; place: string };

@Component({
  selector: 'app-root', standalone: true, imports: [LeafletDirective],
  templateUrl: './app.component.html', styleUrl: './app.component.css'
})
export class AppComponent implements OnDestroy {
  readonly mode = signal('Cargando configuración');
  readonly status = signal('Preparando el mapa…');
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
  readonly countries = signal<CountryOption[]>([]);
  readonly stats = signal<Stats | null>(null);
  readonly tableRows = signal<TableRow[]>([]);
  readonly truncated = signal(false);
  readonly resultCount = signal(0);
  readonly offset = signal(0);
  readonly reproduction = signal(false);
  readonly options: L.MapOptions = { center: L.latLng(18, 0), zoom: 2, minZoom: 2, maxZoom: 8, preferCanvas: true, worldCopyJump: false };
  private map?: L.Map;
  private events = L.layerGroup();
  private timer?: ReturnType<typeof setTimeout>;
  private controller = new AbortController();
  private destroyed = false;
  private activeConfig?: Config;

  async onMapReady(map: L.Map): Promise<void> {
    this.map = map;
    const base = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, noWrap: true, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    const borders = L.geoJSON(undefined, { style: { color: '#334155', weight: 1, fill: false },
      onEachFeature: (feature, layer) => {
        const name = document.createElement('span');
        name.textContent = feature.properties?.NAME_ES ?? feature.properties?.ADMIN ?? 'Sin nombre';
        layer.bindTooltip(name);
      }
    }).addTo(map);
    this.events.addTo(map);
    L.control.layers({ 'OpenStreetMap': base }, { 'Países (Natural Earth)': borders, 'Terremotos': this.events }).addTo(map);
    map.attributionControl.addAttribution('Fronteras: Natural Earth · Datos reales: USGS');
    try {
      borders.addData(await this.readJson<FeatureCollection>('datos/paises.geojson'));
      this.countriesStatus.set('Catálogo de países cargado');
    } catch { this.countriesStatus.set('No se pudo cargar el catálogo de países'); }
    if (this.destroyed) return;
    try {
      const config = await this.readJson<Config>('config.json');
      if (!['demo', 'api'].includes(config.mode)) throw new Error('Modo inválido');
      this.activeConfig = config;
      this.mode.set(config.mode === 'demo' ? 'DEMOSTRACIÓN · datos ficticios' : 'API · datos del backend');
      if (config.mode === 'api') {
        const headers: Record<string, string> = {};
        if (config.skipNgrokWarning) headers['ngrok-skip-browser-warning'] = '1';
        try { this.countries.set(await this.readJson<CountryOption[]>(`${config.apiUrl.replace(/\/$/, '')}/api/paises`, headers)); }
        catch { this.countries.set([]); }
      }
      await this.refresh(config);
    } catch { this.status.set('Error: revisa public/config.json'); }
  }

  private async readJson<T>(url: string, headers: Record<string, string> = {}): Promise<T> {
    const response = await fetch(url, { headers, cache: 'no-store',
      signal: AbortSignal.any([this.controller.signal, AbortSignal.timeout(15000)]) });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json() as Promise<T>;
  }

  private async refresh(config: Config): Promise<void> {
    clearTimeout(this.timer);
    try {
      const base = config.apiUrl.replace(/\/$/, '');
      const url = config.mode === 'demo' ? 'datos/terremotos-demo.geojson' : `${base}/api/eventos${this.query(true)}`;
      const headers: Record<string, string> = {};
      if (config.mode === 'api' && config.skipNgrokWarning) headers['ngrok-skip-browser-warning'] = '1';
      const data = await this.readJson<Events>(url, headers);
      if (this.destroyed) return;
      if (data.type !== 'FeatureCollection' || !Array.isArray(data.features)) throw new Error('Se esperaba FeatureCollection');
      const next = L.layerGroup(); let omitted = 0; let count = 0;
      const rows: TableRow[] = [];
      for (const feature of data.features) {
        const p = feature.properties;
        const c = feature.geometry?.type === 'Point' ? feature.geometry.coordinates : [];
        const [lon, lat, depth] = c;
        const magnitude = p && typeof p.mag === 'number' && Number.isFinite(p.mag) ? p.mag : null;
        const depthOk = typeof depth === 'number' && Number.isFinite(depth);
        rows.push({
          id: String(feature.id ?? 'ND'),
          time: this.date(p?.time),
          mag: magnitude === null ? 'ND' : String(magnitude),
          depth: depthOk ? String(depth) : 'ND',
          country: p?.country_name ?? 'Sin país asignado',
          place: p?.place ?? 'Sin descripción',
        });
        if (!p || !Number.isFinite(lon) || !Number.isFinite(lat) || Math.abs(lon) > 180 || Math.abs(lat) > 90) { omitted++; continue; }
        const color = !depthOk ? '#64748b' : depth < 70 ? '#e8a317' : depth < 300 ? '#e35b37' : '#7b3fb6';
        const popup = document.createElement('div');
        popup.textContent = `${p.place ?? 'Sin descripción'}\nMagnitud: ${magnitude ?? 'ND'}\nProfundidad: ${depthOk ? depth + ' km' : 'ND'}\nFecha UTC: ${this.date(p.time)}\nPaís: ${p.country_name ?? 'Sin país asignado'}\nID: ${feature.id ?? 'ND'}`;
        L.circleMarker([lat, lon], { radius: magnitude === null ? 4 : Math.max(3, Math.min(18, 3 + (magnitude + 1) * 2)), color, fillColor: color, fillOpacity: .75, weight: 1 }).bindPopup(popup).addTo(next);
        count++;
      }
      this.events.clearLayers(); this.events.addLayer(next);
      this.count.set(count); this.omitted.set(omitted); this.tableRows.set(rows);
      this.truncated.set(Boolean(data.metadata?.truncated));
      this.resultCount.set(data.metadata?.count ?? count);
      this.lastRead.set(new Date().toISOString());
      this.generated.set(this.date(data.metadata?.generated));
      this.ingestion.set(this.date(data.metadata?.last_ingestion));
      const ingestedAt = data.metadata?.last_ingestion;
      const ingestaVieja = typeof ingestedAt === 'number' && Number.isFinite(ingestedAt) && Date.now() - ingestedAt > 5 * 60 * 1000;
      this.ingestionWarning.set(ingestaVieja ? 'El productor parece parado: la última ingesta USGS supera 5 minutos, aunque la API responda.' : '');
      if (config.mode === 'api') {
        try {
          this.stats.set(await this.readJson<Stats>(`${base}/api/estadisticas${this.query(false)}`, headers));
        } catch {
          this.status.set('El mapa se actualizó, pero las estadísticas no respondieron.');
          return;
        }
      }
      this.status.set(config.mode === 'demo' ? 'Ejemplo estático: no representa actividad real' : 'API accesible · consulta completada');
    } catch {
      if (!this.destroyed) this.status.set('No se pudo actualizar: se conserva la última lectura. Revisa API, túnel y CORS.');
    } finally {
      if (!this.destroyed && config.mode === 'api') this.timer = setTimeout(() => void this.refresh(config), Math.max(30000, Number(config.refreshMs) || 60000));
    }
  }

  applyFilters(event: Event): void {
    event.preventDefault();
    this.offset.set(0);
    if (this.activeConfig) void this.refresh(this.activeConfig);
  }

  clearFilters(): void {
    this.filterStart.set(''); this.filterEnd.set(''); this.filterMag.set('');
    this.filterCountry.set(''); this.filterRegion.set(''); this.offset.set(0);
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
    const d = new Date(value); return Number.isNaN(d.getTime()) ? 'ND' : d.toISOString();
  }
  ngOnDestroy(): void { this.destroyed = true; clearTimeout(this.timer); this.controller.abort(); }
}

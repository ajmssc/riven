/** Human labels and setup hints for backend `/services` keys (see default.py get_services). */

const LABELS: Record<string, string> = {
  realdebrid: 'Real-Debrid',
  alldebrid: 'AllDebrid',
  debridlink: 'Debrid-Link',
  torbox: 'TorBox',
  torrentio: 'Torrentio',
  aiostreams: 'AIOStreams',
  comet: 'Comet',
  jackett: 'Jackett',
  mediafusion: 'Mediafusion',
  orionoid: 'Orionoid',
  prowlarr: 'Prowlarr',
  rarbg: 'RARBG',
  zilean: 'Zilean',
  overseerr: 'Overseerr',
  plexwatchlist: 'Plex watchlist',
  listrr: 'Listrr',
  mdblist: 'MDBList',
  traktcontent: 'Trakt',
  indexer: 'Indexer',
  post_processing: 'Post-processing',
  subtitle: 'Subtitles',
  notifications: 'Notifications',
  filesystem: 'Filesystem (VFS)',
  plexupdater: 'Plex library refresh',
  jellyfinupdater: 'Jellyfin library refresh',
  embyupdater: 'Emby library refresh',
  consoleupdater: 'Console updater (placeholder)',
};

/** Short guidance when a service reports initialized === false. */
const SETUP_HELP: Record<string, string> = {
  overseerr:
    'Add your Overseerr base URL and API key under Content, and enable the integration.',
  plexwatchlist: 'Enable Plex watchlist sync and complete Plex authentication in settings.',
  listrr: 'Enable Listrr and set its URL / API key under Content.',
  mdblist: 'Enable MDBList and configure your API key under Content.',
  traktcontent: 'Enable Trakt and add OAuth credentials or API key under Content.',
  realdebrid: 'Enable Real-Debrid and paste a valid API key under Downloaders.',
  alldebrid: 'Enable AllDebrid and paste a valid API key under Downloaders.',
  debridlink: 'Enable Debrid-Link and configure API access under Downloaders.',
  torbox: 'Enable TorBox and set your API key under Downloaders.',
  torrentio: 'Enable Torrentio and set its URL or options under Scrapers.',
  aiostreams: 'Enable AIOStreams and provide required API configuration under Scrapers.',
  comet: 'Enable Comet and set API key / URL as required under Scrapers.',
  jackett: 'Enable Jackett and point Riven at your Jackett URL and API key.',
  mediafusion: 'Enable Mediafusion and complete its API settings under Scrapers.',
  orionoid: 'Enable Orionoid and add your API key under Scrapers.',
  prowlarr: 'Enable Prowlarr and configure its base URL and API key under Scrapers.',
  rarbg: 'Enable RARBG / mirror settings if you still use this scraper.',
  zilean: 'Enable Zilean and set host, API key, or DMM options under Scrapers.',
  indexer: 'Configure TMDB and/or TVDB API keys under Indexers so metadata can resolve.',
  plexupdater: 'Under Updaters → Plex, set server URL, token, and library mapping for library refresh.',
  jellyfinupdater: 'Under Updaters → Jellyfin, set server URL and API key for library refresh.',
  embyupdater: 'Under Updaters → Emby, set server URL and API key for library refresh.',
  consoleupdater:
    'No Plex/Jellyfin/Emby updater is configured; Riven is using a no-op console updater. Add a real media server under Updaters if you want automatic library refresh.',
  filesystem:
    'With FUSE enabled, install pyfuse3, set mount_path, and ensure the mount succeeds. If you intentionally run without FUSE, only the in-memory mount inventory is used.',
  post_processing: 'Review post-processing settings; sub-services may be disabled or misconfigured.',
  subtitle:
    'Enable subtitles under Post-processing, pick languages, and enable at least one provider (e.g. OpenSubtitles) with credentials.',
  notifications:
    'Enable notifications and add at least one Apprise service URL, or leave disabled if you do not need external alerts.',
};

function normalizeKey(serviceKey: string): string {
  return serviceKey.toLowerCase().replace(/\s+/g, '');
}

export function humanizeServiceKey(serviceKey: string): string {
  const k = normalizeKey(serviceKey);
  if (LABELS[k]) return LABELS[k];
  return k
    .replace(/_/g, ' ')
    .replace(/\b([a-z])/g, (m) => m.toUpperCase());
}

export function getServiceNotConfiguredWarning(serviceKey: string): string {
  const k = normalizeKey(serviceKey);
  return (
    SETUP_HELP[k] ??
    'Not initialized — enable it in Settings if you need it, add API keys or URLs, and check connectivity.'
  );
}

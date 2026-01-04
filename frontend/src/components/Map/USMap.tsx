import { useEffect, useRef, useState } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { useNavigate } from 'react-router-dom'
import type { StateAggregation } from '../../api/types'

// Mapbox access token - public tokens (pk.*) are safe to expose
// They are secured via domain restrictions in Mapbox dashboard
const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN || 'pk.eyJ1IjoiYmVudG9ubW9zcyIsImEiOiJjbWswN3AzYzM2eWNnM2VwczY1cTVqbm45In0.Hal891JmlnwoYSUv8K99Jg'
if (MAPBOX_TOKEN) {
  mapboxgl.accessToken = MAPBOX_TOKEN
}

interface USMapProps {
  statesData: StateAggregation[]
  onStateClick?: (stateCode: string) => void
}

// US State boundaries GeoJSON URL (public)
const US_STATES_GEOJSON = 'https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json'

// State name to code mapping
const STATE_CODES: Record<string, string> = {
  'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
  'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
  'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
  'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
  'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
  'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
  'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
  'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
  'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
  'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
  'District of Columbia': 'DC'
}

export default function USMap({ statesData, onStateClick }: USMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<mapboxgl.Map | null>(null)
  const navigate = useNavigate()
  const [mapLoaded, setMapLoaded] = useState(false)
  const [mapError, setMapError] = useState<string | null>(null)

  useEffect(() => {
    if (!mapContainer.current || map.current) return

    if (!MAPBOX_TOKEN) {
      setMapError('Mapbox token not configured. Please set VITE_MAPBOX_ACCESS_TOKEN.')
      return
    }

    try {
      map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: [-98.5795, 39.8283], // Center of US
      zoom: 3.5,
      minZoom: 2,
      maxZoom: 8,
    })

    map.current.addControl(new mapboxgl.NavigationControl(), 'top-right')

    map.current.on('load', () => {
      setMapLoaded(true)
    })

    map.current.on('error', (e) => {
      console.error('Mapbox error:', e)
      setMapError('Failed to load map. Please check your Mapbox token.')
    })

    } catch (err) {
      console.error('Map initialization error:', err)
      setMapError('Failed to initialize map.')
    }

    return () => {
      map.current?.remove()
      map.current = null
    }
  }, [])

  useEffect(() => {
    if (!mapLoaded || !map.current || statesData.length === 0) return

    // Create a lookup for state data
    const stateDataMap = new Map(statesData.map(s => [s.state, s]))

    // Fetch and add states layer
    fetch(US_STATES_GEOJSON)
      .then(res => res.json())
      .then(geojson => {
        // Enrich GeoJSON with our data
        geojson.features = geojson.features.map((feature: any) => {
          const stateName = feature.properties.name
          const stateCode = STATE_CODES[stateName]
          const data = stateDataMap.get(stateCode)

          return {
            ...feature,
            properties: {
              ...feature.properties,
              stateCode,
              ...data,
            },
          }
        })

        // Add source
        if (map.current?.getSource('states')) {
          (map.current.getSource('states') as mapboxgl.GeoJSONSource).setData(geojson)
        } else {
          map.current?.addSource('states', {
            type: 'geojson',
            data: geojson,
          })

          // Add fill layer with party-based coloring
          map.current?.addLayer({
            id: 'states-fill',
            type: 'fill',
            source: 'states',
            paint: {
              'fill-color': [
                'case',
                ['>', ['get', 'democrats'], ['get', 'republicans']],
                '#2563eb', // Democrat blue
                ['>', ['get', 'republicans'], ['get', 'democrats']],
                '#dc2626', // Republican red
                '#7c3aed', // Purple for tie/independent
              ],
              'fill-opacity': [
                'interpolate',
                ['linear'],
                ['coalesce', ['get', 'avg_transparency_score'], 50],
                0, 0.3,
                100, 0.8,
              ],
            },
          })

          // Add border layer
          map.current?.addLayer({
            id: 'states-border',
            type: 'line',
            source: 'states',
            paint: {
              'line-color': '#374151',
              'line-width': 1,
            },
          })

          // Hover state
          map.current?.addLayer({
            id: 'states-hover',
            type: 'fill',
            source: 'states',
            paint: {
              'fill-color': '#fbbf24',
              'fill-opacity': 0.5,
            },
            filter: ['==', 'name', ''],
          })

          // Click handler
          map.current?.on('click', 'states-fill', (e) => {
            const stateCode = e.features?.[0]?.properties?.stateCode
            if (stateCode) {
              if (onStateClick) {
                onStateClick(stateCode)
              } else {
                navigate(`/state/${stateCode}`)
              }
            }
          })

          // Hover handlers
          map.current?.on('mouseenter', 'states-fill', () => {
            if (map.current) {
              map.current.getCanvas().style.cursor = 'pointer'
            }
          })

          map.current?.on('mousemove', 'states-fill', (e) => {
            if (e.features && e.features.length > 0) {
              map.current?.setFilter('states-hover', ['==', 'name', e.features[0].properties?.name])
            }
          })

          map.current?.on('mouseleave', 'states-fill', () => {
            if (map.current) {
              map.current.getCanvas().style.cursor = ''
              map.current.setFilter('states-hover', ['==', 'name', ''])
            }
          })

          // Popup on hover
          const popup = new mapboxgl.Popup({
            closeButton: false,
            closeOnClick: false,
          })

          map.current?.on('mousemove', 'states-fill', (e) => {
            if (!e.features || e.features.length === 0) return

            const props = e.features[0].properties
            if (!props) return

            const html = `
              <div class="p-2">
                <h3 class="font-bold text-lg">${props.name}</h3>
                <div class="text-sm space-y-1 mt-2">
                  <p><span class="text-blue-600 font-medium">D: ${props.democrats || 0}</span> |
                     <span class="text-red-600 font-medium">R: ${props.republicans || 0}</span> |
                     <span class="text-purple-600 font-medium">I: ${props.independents || 0}</span></p>
                  <p>Senators: ${props.senators || 0} | Reps: ${props.representatives || 0}</p>
                  ${props.avg_transparency_score ?
                    `<p>Avg Transparency: <span class="font-medium">${props.avg_transparency_score.toFixed(1)}</span></p>` : ''}
                </div>
                <p class="text-xs text-gray-500 mt-2">Click to view details</p>
              </div>
            `

            popup
              .setLngLat(e.lngLat)
              .setHTML(html)
              .addTo(map.current!)
          })

          map.current?.on('mouseleave', 'states-fill', () => {
            popup.remove()
          })
        }
      })
  }, [mapLoaded, statesData, navigate, onStateClick])

  if (mapError) {
    return (
      <div className="relative w-full h-full min-h-[500px] rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center">
        <div className="text-center p-8">
          <p className="text-red-600 font-medium">{mapError}</p>
          <p className="text-gray-500 text-sm mt-2">The interactive map requires a valid Mapbox token.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="relative w-full h-full min-h-[500px] rounded-lg overflow-hidden">
      <div ref={mapContainer} className="absolute inset-0" />
      {!mapLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      )}
    </div>
  )
}

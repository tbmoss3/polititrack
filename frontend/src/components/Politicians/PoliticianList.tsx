import type { Politician } from '../../api/types'
import PoliticianCard from './PoliticianCard'

interface PoliticianListProps {
  politicians: Politician[]
  title?: string
}

export default function PoliticianList({ politicians, title }: PoliticianListProps) {
  if (politicians.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No politicians found
      </div>
    )
  }

  return (
    <div>
      {title && (
        <h2 className="text-xl font-semibold text-gray-900 mb-4">{title}</h2>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {politicians.map((politician) => (
          <PoliticianCard key={politician.id} politician={politician} />
        ))}
      </div>
    </div>
  )
}

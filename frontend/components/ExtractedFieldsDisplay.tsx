'use client';

interface ExtractedField {
  [key: string]: string | number | boolean | null | undefined;
}

interface ExtractedFieldsDisplayProps {
  data: ExtractedField | null;
  title: string;
  color: 'blue' | 'green';
}

export default function ExtractedFieldsDisplay({
  data,
  title,
  color,
}: ExtractedFieldsDisplayProps) {
  if (!data) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
        <p className="text-gray-500">No data available</p>
      </div>
    );
  }

  const bgColor = color === 'blue' ? 'bg-blue-50' : 'bg-green-50';
  const borderColor = color === 'blue' ? 'border-blue-200' : 'border-green-200';
  const titleColor = color === 'blue' ? 'text-blue-700' : 'text-green-700';
  const titleBgColor = color === 'blue' ? 'bg-blue-100' : 'bg-green-100';

  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return '—';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (Array.isArray(value)) return value.join(', ');
    return String(value);
  };

  const entries = Object.entries(data).filter(([, value]) => value !== null && value !== undefined);

  return (
    <div className={`border border-gray-200 rounded-lg overflow-hidden ${bgColor}`}>
      {/* Header */}
      <div className={`${titleBgColor} px-6 py-3 border-b border-gray-200`}>
        <h3 className={`${titleColor} font-bold text-lg`}>{title}</h3>
      </div>

      {/* Fields */}
      <div className="divide-y divide-gray-200">
        {entries.length === 0 ? (
          <div className="px-6 py-4 text-center text-gray-500">
            No fields extracted
          </div>
        ) : (
          entries.map(([key, value], index) => (
            <div
              key={index}
              className="px-6 py-4 hover:bg-white/50 transition-colors flex justify-between items-start gap-4"
            >
              <label className="font-medium text-gray-700 flex-shrink-0 min-w-40">
                {key.replace(/_/g, ' ')}:
              </label>
              <span className="text-gray-600 text-right break-words flex-1">
                {formatValue(value)}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}


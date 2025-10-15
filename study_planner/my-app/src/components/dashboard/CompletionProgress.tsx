import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const subjects = [
  { name: "General Histology", progress: 79, color: "hsl(var(--primary))" },
  { name: "Living (surface) Anatomy", progress: 91, color: "hsl(var(--success))" },
  { name: "Neuroanatomy", progress: 25, color: "hsl(var(--danger))" },
  { name: "Regional Anatomy: ABDOMEN", progress: 97, color: "hsl(var(--info))" },
];

function CircularProgress({ progress, color }: { progress: number; color: string }) {
  const radius = 30;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <div className="relative w-20 h-20">
      <svg className="w-full h-full transform -rotate-90">
        <circle
          cx="40"
          cy="40"
          r={radius}
          fill="none"
          stroke="hsl(var(--border))"
          strokeWidth="6"
        />
        <circle
          cx="40"
          cy="40"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-300"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-sm font-bold">{progress}%</span>
      </div>
    </div>
  );
}

export function CompletionProgress() {
  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="flex-shrink-0">
        <CardTitle className="text-lg font-semibold">Completion Progress</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto space-y-4">
        {subjects.map((subject) => (
          <div key={subject.name} className="flex items-center justify-between">
            <span className="text-sm font-medium flex-1">{subject.name}</span>
            <CircularProgress progress={subject.progress} color={subject.color} />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
export default CompletionProgress;
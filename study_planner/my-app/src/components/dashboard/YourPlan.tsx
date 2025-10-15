import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FileText, Image } from "lucide-react";

const planItems = [
  {
    id: 6,
    date: 8,
    color: "bg-warning",
    title: "Item 6",
    description: "Hey! I just finished the first chapter",
    time: "09:34 am",
    files: ["First Chapter of Project .doc"],
  },
  {
    id: 7,
    date: 13,
    color: "bg-danger",
    title: "Item 7",
    description: "Can you please fill the formulas in these images att...",
    time: "12:30 pm",
    files: ["Image .jpg", "form .jpg", "Image 2 .jpg"],
  },
  {
    id: 8,
    date: 18,
    color: "bg-success",
    title: "Item 8",
    description: "Dear Aya, You are yet to submit your assignment for chap...",
    time: "16:30 pm",
  },
];

export function YourPlan() {
  return (
    <Card className="flex flex-col">
      <CardHeader className="flex-shrink-0 flex flex-row items-center justify-between">
        <CardTitle className="text-lg font-semibold">Your Plan</CardTitle>
        <button className="text-sm text-primary hover:underline">View All</button>
      </CardHeader>
      <CardContent className="overflow-y-auto max-h-[400px] space-y-4">
        {planItems.map((item) => (
          <div key={item.id} className="flex items-start gap-3">
            <div
              className={`${item.color} text-white rounded-full w-12 h-12 flex items-center justify-center flex-shrink-0 font-bold text-lg`}
            >
              {item.date}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2 mb-1">
                <h4 className="font-semibold">{item.title}</h4>
                <span className="text-xs text-muted-foreground whitespace-nowrap">{item.time}</span>
              </div>
              <p className="text-sm text-muted-foreground mb-2">{item.description}</p>

              {item.files && (
                <div className="flex flex-wrap gap-2">
                  {item.files.map((file, idx) => (
                    <Badge
                      key={idx}
                      variant="outline"
                      className="text-xs gap-1 bg-primary/5 text-primary border-primary/20"
                    >
                      {file.includes("Image") ? (
                        <Image className="w-3 h-3" />
                      ) : (
                        <FileText className="w-3 h-3" />
                      )}
                      {file}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
export default YourPlan;
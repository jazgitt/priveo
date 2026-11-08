import {
  CircleCheckIcon,
  InfoIcon,
  Loader2Icon,
  OctagonXIcon,
  TriangleAlertIcon,
} from "lucide-react"
import { Toaster as Sonner, type ToasterProps } from "sonner"

/** The toast host: bottom right, the portal's light theme. The bar is larger, and an error fills deep red (ux9); the position is unchanged. */
const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="light"
      position="bottom-right"
      closeButton
      className="toaster group"
      toastOptions={{
        classNames: {
          toast: "!w-[26rem] !max-w-[calc(100vw-2rem)] !min-h-16 !px-5 !py-4 !shadow-xl",
          title: "!text-base !font-semibold",
          description: "!text-sm",
          error: "!bg-[#8b1a1a] !border-[#5c0f0f] !text-white [&_[data-description]]:!text-white/90 [&_[data-title]]:!text-white",
        },
      }}
      icons={{
        success: <CircleCheckIcon className="size-4 text-ok" />,
        info: <InfoIcon className="size-4 text-info" />,
        warning: <TriangleAlertIcon className="size-4 text-warn" />,
        error: <OctagonXIcon className="size-4 text-destructive" />,
        loading: <Loader2Icon className="size-4 animate-spin" />,
      }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
        } as React.CSSProperties
      }
      {...props}
    />
  )
}

export { Toaster }

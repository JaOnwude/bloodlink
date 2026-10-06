import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"

/**
 * Button styles for BloodLink.
 *
 * Buttons are pill-shaped with generous touch targets (the default is 44px tall). Every
 * value comes from the design tokens in styles/globals.css.
 *
 * To make a link look like a button, apply the styles to the link itself:
 *
 *   <Link href="/register" className={buttonVariants({ variant: "default", size: "lg" })}>
 *
 * The `link` and `arrow` variants are text-style actions; give `arrow` an icon child and it
 * nudges forward on hover.
 */
const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center gap-2 rounded-full border border-transparent font-medium whitespace-nowrap transition-[background-color,color,border-color,box-shadow,transform] duration-250 ease-brand outline-none select-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background active:translate-y-px disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground shadow-soft hover:bg-primary-700 hover:shadow-lift",
        outline:
          "border-ink/80 bg-transparent text-ink hover:bg-ink hover:text-background",
        secondary: "bg-secondary text-secondary-foreground hover:bg-primary-100",
        ghost: "text-ink hover:bg-muted",
        destructive: "bg-destructive text-white hover:bg-destructive/90",
        link: "rounded-md text-primary underline-offset-4 hover:underline",
        arrow:
          "rounded-md font-semibold text-primary hover:[&_svg]:translate-x-1 [&_svg]:transition-transform [&_svg]:duration-250",
      },
      size: {
        default: "h-11 px-6 text-sm",
        xs: "h-7 px-3 text-xs",
        sm: "h-9 px-4 text-sm",
        lg: "h-12 px-7 text-base",
        xl: "h-14 px-9 text-base",
        icon: "size-11",
        "icon-xs": "size-7",
        "icon-sm": "size-9",
        "icon-lg": "size-12",
      },
    },
    compoundVariants: [
      // Text-style actions carry no button padding or fixed height.
      { variant: ["link", "arrow"], class: "h-auto! px-0!" },
    ],
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }

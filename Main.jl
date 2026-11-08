# Julia-Set-Gen: render a Julia set (f(z) = z^2 + c) to a PNG.
#
#   julia --project=. Main.jl                                 # the classic c = -0.8 + 0.156im
#   julia --project=. Main.jl --c=0.285+0.01im --palette=inferno --iter=300
#   julia --project=. Main.jl --zoom=4 --center=-0.2,0.1 --size=1200x900 --out=zoom.png
#
# Options: --c  --palette (any ColorSchemes name, or "cursed")  --zoom  --center=x,y
#          --iter (max iterations)  --size=WxH  --out (PNG file)

using ColorSchemes
using PNGFiles

# How many iterations z -> z^2 + c takes to leave the circle |z| <= 2, smoothed so the colours
# blend instead of banding. Points that never leave (the set itself) get max_iter.
function julia(c, z, max_iter)
    n = 0
    while abs(z) <= 2 && n < max_iter
        z = z^2 + c
        n += 1
    end
    n == max_iter && return Float64(max_iter)
    return n + 1 - log2(log2(abs(z)))
end

# One escape value per pixel, over the rectangle [x_min, x_max] x [y_min, y_max] of the complex plane.
function generate_julia(width, height, x_min, x_max, y_min, y_max, c, max_iter)
    image = zeros(Float64, height, width)
    Threads.@threads for x in 1:width
        real = x_min + (x - 1) * (x_max - x_min) / (width - 1)
        for y in 1:height
            imag = y_max - (y - 1) * (y_max - y_min) / (height - 1)   # top row = top of the plane
            image[y, x] = julia(c, complex(real, imag), max_iter)
        end
    end
    return image
end

# Escape values -> colours. The set itself is drawn in the darkest colour of the palette.
function colour_julia(image, max_iter, scheme)
    escaped = [v for v in image if v < max_iter]
    lo, hi = isempty(escaped) ? (0.0, 1.0) : extrema(escaped)
    return map(image) do v
        v >= max_iter ? get(scheme, 0.0) : get(scheme, clamp((v - lo) / max(hi - lo, eps()), 0, 1)^0.5)
    end
end

const CURSED = ColorScheme([ColorSchemes.RGB(0.07, 0.07, 0.09), ColorSchemes.RGB(0.0, 0.32, 0.52),
                            ColorSchemes.RGB(0.88, 0.25, 0.54), ColorSchemes.RGB(1.0, 1.0, 1.0)])

function options(args)
    o = Dict("c" => "-0.8+0.156im", "palette" => "hot", "zoom" => "1", "center" => "0,0",
             "iter" => "100", "size" => "800x600", "out" => "julia.png")
    for a in args
        k, v = split(lstrip(a, '-'), '='; limit = 2)
        haskey(o, k) || error("unknown option --$k")
        o[k] = v
    end
    return o
end

function main(args)
    o = options(args)
    c = parse(ComplexF64, o["c"])
    width, height = parse.(Int, split(o["size"], 'x'))
    max_iter = parse(Int, o["iter"])
    zoom = parse(Float64, o["zoom"])
    cx, cy = parse.(Float64, split(o["center"], ','))
    scheme = o["palette"] == "cursed" ? CURSED : ColorSchemes.colorschemes[Symbol(o["palette"])]

    # The default view shows x in [-2, 2]; zoom shrinks it around the centre, keeping the aspect.
    half_w = 2 / zoom
    half_h = half_w * height / width
    image = generate_julia(width, height, cx - half_w, cx + half_w, cy - half_h, cy + half_h, c, max_iter)
    PNGFiles.save(o["out"], colour_julia(image, max_iter, scheme))
    println("Saved $(o["out"]): c = $c, $(width)x$(height), $max_iter iterations, zoom $zoom, palette $(o["palette"])")
end

main(ARGS)

using Plots

function julia(c, z, max_iter)
    n = 0
    while abs(z) <= 2 && n < max_iter
        z = z^2 + c
        n += 1
    end
    return n + 1 - log2(log2(abs(z)))
end

function generate_julia(width, height, x_min, x_max, y_min, y_max, c, max_iter)
    image = zeros(Float64, height, width)

    for x in 1:width
        for y in 1:height
            real = x_min + x * (x_max - x_min) / (width - 1)
            imag = y_min + y * (y_max - y_min) / (height - 1)
            z = complex(real, imag)
            color = julia(c, z, max_iter)
            image[y, x] = color
        end
    end

    return image
end

function plot_julia(image, x_min, x_max, y_min, y_max)
    heatmap(x_min:((x_max - x_min) / (size(image, 2) - 1)):x_max,
            y_min:((y_max - y_min) / (size(image, 1) - 1)):y_max,
            image,
            c=:hot,
            xlabel="Real",
            ylabel="Imaginary",
            title="Julia Set",
            color=:auto)
end

# Set the parameters
width, height = 800, 600
x_min, x_max = -2, 2
y_min, y_max = -1.5, 1.5
c = -0.8 + 0.156im
max_iter = 100

# Generate and plot the Julia set
julia_image = generate_julia(width, height, x_min, x_max, y_min, y_max, c, max_iter)
plot_julia(julia_image, x_min, x_max, y_min, y_max)

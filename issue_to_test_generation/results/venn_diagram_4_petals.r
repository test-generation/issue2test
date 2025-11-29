# 📌 Install and Load Required Libraries (Run Once)
if (!require("ggvenn")) {
    install.packages("ggvenn", dependencies = TRUE)
    library(ggvenn)
} else {
    library(ggvenn)
}

if (!require("ggplot2")) {
    install.packages("ggplot2", dependencies = TRUE)
    library(ggplot2)
} else {
    library(ggplot2)
}

# 📌 Load the Data
file_path <- "/Users/nashid/repos/issue-to-test/swt-bench/venn_data_0.csv"
if (!file.exists(file_path)) stop("❌ Error: venn_data.csv not found!")

data <- read.csv(file_path, stringsAsFactors = FALSE)

# 📌 Convert Data into a Named List for the Venn Diagram
venn_data <- split(data$Instances, data$Technique)

# 🎨 **4-Set Venn Diagram (Manually Adjusted Labels)**
venn_plot <- ggvenn(
  venn_data,
  fill_color = c("#E63946", "#457B9D", "#F4A261", "#2A9D8F"),  # ✅ Professional colors
  stroke_size = 1.5,  # ✅ Thicker borders for clarity
  set_name_size = 7,  # ✅ Bigger technique labels
  text_size = 9,  # ✅ Bigger numbers inside petals
  show_percentage = FALSE
) +
  theme_minimal() +
  theme(
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA),
    plot.title = element_text(hjust = 0.5, face = "bold", size = 18),  # ✅ ICSE-style bold title
    legend.position = "none",  # ✅ Remove clutter
    panel.grid = element_blank(),  # ✅ Remove grid lines
    axis.text = element_blank(),  # ✅ Remove x and y axis text (numbers)
    axis.ticks = element_blank(),  # ✅ Remove axis ticks
    axis.title = element_blank(),  # ✅ Remove axis labels
  )

# ✅ FIX: Move Labels Closer Manually
venn_plot <- venn_plot + theme(
    plot.margin = margin(0, 0, 10, 0)  # ✅ Reducing spacing to bring labels closer
)

# 📌 Save **High-Quality** Image
output_file <- "/Users/nashid/repos/issue-to-test/swt-bench/petal_venn.png"
ggsave(output_file, plot = venn_plot, width = 12, height = 10, dpi = 1200, bg = "white")  # ✅ High resolution

print(paste("✅ Clean White-Background Venn Diagram saved at:", output_file))

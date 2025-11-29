# 📌 Install Required Libraries
if (!require("ggVennDiagram")) install.packages("ggVennDiagram", dependencies=TRUE)
if (!require("ggplot2")) install.packages("ggplot2", dependencies=TRUE)
library(ggVennDiagram)
library(ggplot2)

# 📌 Load the Data
file_path <- "./venn_data.csv"
if (!file.exists(file_path)) stop("❌ Error: venn_data.csv not found!")

data <- read.csv(file_path, stringsAsFactors=FALSE)

# 🚨 Ensure columns exist and are correctly named
if (!all(c("Instances", "Technique") %in% colnames(data))) {
  stop("❌ Error: Required columns ('Instances' and 'Technique') not found!")
}

# 📌 Convert Data into a Named List for Venn Diagram
venn_data <- split(data$Instances, data$Technique)
venn_data <- lapply(venn_data, function(x) unique(as.character(x)))  # 🚨 Ensure each set is a unique character vector

# 🚩 Explicitly set technique names and order
techniques_order <- c("LIBRO", "AutoCodeRover", "SWE-Agent+", "Auto-TDD", "Issue2Test")
venn_data <- venn_data[techniques_order]

# 🚨 Check explicitly for empty or NULL sets
empty_sets <- names(venn_data)[sapply(venn_data, length) == 0 | sapply(venn_data, is.null)]
if (length(empty_sets) > 0) stop(paste("❌ Error: The following sets are empty:", paste(empty_sets, collapse=", ")))

# 🎨 Create Venn Diagram
venn_plot <- ggVennDiagram(
  venn_data,
  category.names = techniques_order,
  # Appearance
  label = "count",
  label_size = 14,
  label_style = list(fontface = "bold"),
  edge_size = 2,
  set_size = 13,
  set_style = list(fontface = "bold"),
) +
  scale_fill_gradient(low="#F4FAFE", high="#4981BF") +
  theme_void() +
  theme(
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA),
    legend.position = "none",
    plot.margin = margin(30, 30, 30, 30)
  )

# 📌 Save **High-Quality** Image
output_file <- "./petal_venn_5_sets.png"
ggsave(output_file, venn_plot, width = 20, height = 24, dpi = 1200, bg = "white")

print(paste("✅ Venn Diagram saved at:", output_file))
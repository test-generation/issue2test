# Install required packages
Rscript -e "options(repos = c(CRAN = 'https://cloud.r-project.org/')); \
if (!requireNamespace('ggVennDiagram', quietly = TRUE)) install.packages('ggVennDiagram'); \
if (!requireNamespace('ggplot2', quietly = TRUE)) install.packages('ggplot2')"

# Generate Venn diagram
Rscript -e "library(ggVennDiagram); source('venn_diagram.r')"

# Trim output images
magick petal_venn_5_sets.png -trim +repage petal_venn_5_sets.png

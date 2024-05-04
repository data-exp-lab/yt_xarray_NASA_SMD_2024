if [[ $# -eq 0 ]]; then
  OPSTRNG="-h"
else
  OPSTRNG="$1"
fi


BUILD_DIR="yt_xr_2024/_build"

if [[ $OPSTRNG == *"help"* ]] || [[ "$OPSTRNG" = "-h" ]]; then
  echo "\n"
  echo "To clean out the build directory: "
  echo "    $ ./build_pdf.sh clean"
  echo "To rebuild pdf"
  echo "    $ ./build_pdf.sh build"
  echo "To build html"
  echo "    $ ./build_pdf.sh html"
  echo "To run multiple, use comma separated list:"
  echo "    $ ./build_pdf.sh clean,build"
  echo "\n"
fi

if [[ $OPSTRNG == *"clean"* ]] && [[ -d "$BUILD_DIR" ]]; then
  echo "Clearing out build directory."
  rm -r $BUILD_DIR
fi

if [[ $OPSTRNG == *"build"* ]]; then
  jupyter-book build yt_xr_2024/ --builder pdflatex
  cp yt_xr_2024/_build/latex/yt_xr_2024.pdf ./yt_xr_2024.pdf
  echo "Copied pdfoutput to yt_xr_2024.pdf"
fi

if [[ $OPSTRNG == *"html"* ]]; then
  jupyter-book build yt_xr_2024/
fi

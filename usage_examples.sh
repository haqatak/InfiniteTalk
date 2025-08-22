#!/bin/bash

# ============================================================================
# InfiniteTalk Usage Example Script
# ============================================================================
# This script demonstrates how to use InfiniteTalk for video generation
# ============================================================================

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=========================================="
echo -e "  InfiniteTalk Usage Examples"
echo -e "==========================================${NC}"
echo ""

echo -e "${BLUE}1. Web Interface (Recommended)${NC}"
echo "   • Open: http://localhost:8000"
echo "   • Upload audio file and reference image"
echo "   • Enter a prompt (e.g., 'A person speaking naturally')"
echo "   • Click 'Generate Video'"
echo "   • Monitor progress and view results"
echo ""

echo -e "${BLUE}2. Command Line Usage${NC}"
echo "   # Using example files:"
echo "   python generate_infinitetalk.py \\"
echo "     --task infinitetalk_lightx2v \\"
echo "     --config_path examples/single_example_image.json \\"
echo "     --ckpt_dir weights/InfiniteTalk \\"
echo "     --sample_steps 4 \\"
echo "     --output_dir outputs/"
echo ""

echo -e "${BLUE}3. API Usage (curl)${NC}"
echo "   # Generate video via API:"
echo "   curl -X POST 'http://localhost:8000/api/generate' \\"
echo "     -F 'audio=@path/to/audio.wav' \\"
echo "     -F 'image=@path/to/image.jpg' \\"
echo "     -F 'prompt=A person speaking naturally'"
echo ""

echo -e "${BLUE}4. Server Management${NC}"
echo "   ./start_infinitetalk.sh start     # Start server"
echo "   ./start_infinitetalk.sh stop      # Stop server"
echo "   ./start_infinitetalk.sh restart   # Restart server"
echo "   ./start_infinitetalk.sh status    # Check status"
echo "   ./start_infinitetalk.sh download  # Download models"
echo ""

echo -e "${BLUE}5. Example Configuration (JSON)${NC}"
echo "   {"
echo "     \"prompt\": \"A person speaking naturally\","
echo "     \"cond_video\": \"path/to/reference_image.jpg\","
echo "     \"cond_audio\": {"
echo "       \"person1\": \"path/to/audio.wav\""
echo "     }"
echo "   }"
echo ""

echo -e "${YELLOW}Quick Test:${NC}"
echo "1. Ensure server is running: ./start_infinitetalk.sh status"
echo "2. Open web interface: http://localhost:8000"
echo "3. Use example files from examples/ directory"
echo "4. Check outputs in api/outputs/ directory"
echo ""

echo -e "${GREEN}For support, check:${NC}"
echo "• Server logs: tail -f server.log"
echo "• Setup guide: cat SETUP_GUIDE.md"
echo "• API docs: http://localhost:8000/docs"

# Dish Photos Dropzone 📸

Drop your authentic dish photos into this folder!

### How to use:
1. Save or copy your dish photos into this `dish_photos/` folder.
2. Name your image file after the dish (or close to it), for example:
   - `Chicken Karahi.jpg`
   - `Biryani.png`
   - `aloo_palak.jpeg`
   - `Mutton Qorma.webp`
   - `Daal Chana.jpg`
   - `Nihari.png`
   - `Seekh Kebab.jpg`
3. Run the sync command in terminal:
   ```bash
   python3 scripts/sync_dish_images.py
   ```
   Or visit `/sync_dish_photos` in the Chef Chat web app!

### What the sync script does automatically:
- ✨ Automatically matches your photo filename to the dish name in the database and excel sheet.
- 📁 Copies and organizes the image into `static/images/dishes/`.
- 📊 Updates `data/dishes.csv` and generates `data/dishes.xlsx` (Excel spreadsheet) with the new image link.
- 🔄 Updates `kitchen.db` so the dish instantly shows your authentic photo across Chef Chat (Today, Weekly Plan, Recipes, Friends)!

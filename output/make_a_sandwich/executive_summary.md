# Process Executive Summary

## Process Overview
This process consists of 14 steps and 0 notes.

## Step Summaries
### Gather Ingredients
- **Description**: Check if all required ingredients are available
- **Decision**: Are all ingredients available?
- **Success Path**: Check Bread Freshness
- **Failure Path**: Go to Store

### Go to Store
- **Description**: Go to the nearest store to purchase missing ingredients
- **Decision**: Were you able to purchase all missing ingredients?
- **Success Path**: Check Bread Freshness
- **Failure Path**: End

### Check Bread Freshness
- **Description**: Examine bread to ensure it's fresh
- **Decision**: Is the bread fresh and without mold?
- **Success Path**: Prepare Base
- **Failure Path**: Replace Bread

### Replace Bread
- **Description**: Get new bread from pantry or store
- **Decision**: Was fresh bread obtained?
- **Success Path**: Prepare Base
- **Failure Path**: End

### Prepare Base
- **Description**: Apply condiments to bread slices
- **Decision**: Are condiments spread evenly?
- **Success Path**: Add Main Ingredients
- **Failure Path**: Clean Up and Restart

### Add Main Ingredients
- **Description**: Layer cheese lettuce and tomato on bread
- **Decision**: Are ingredients arranged properly?
- **Success Path**: Final Assembly
- **Failure Path**: Rearrange Ingredients

### Rearrange Ingredients
- **Description**: Fix the arrangement of ingredients
- **Decision**: Is the arrangement now stable?
- **Success Path**: Final Assembly
- **Failure Path**: Start Over

### Final Assembly
- **Description**: Place top slice of bread and press gently
- **Decision**: Is the sandwich properly assembled?
- **Success Path**: Cut Sandwich
- **Failure Path**: Fix Assembly

### Fix Assembly
- **Description**: Readjust the sandwich components
- **Decision**: Is the sandwich now stable?
- **Success Path**: Cut Sandwich
- **Failure Path**: Start Over

### Cut Sandwich
- **Description**: Cut sandwich diagonally or straight across
- **Decision**: Is the cut clean and even?
- **Success Path**: Serve Sandwich
- **Failure Path**: Adjust Cut

### Adjust Cut
- **Description**: Realign the sandwich and make a new cut
- **Decision**: Is the new cut acceptable?
- **Success Path**: Serve Sandwich
- **Failure Path**: Serve Sandwich Uncut

### Serve Sandwich
- **Description**: Place sandwich on plate with presentation
- **Decision**: Is the presentation appetizing?
- **Success Path**: End
- **Failure Path**: Improve Presentation

### Improve Presentation
- **Description**: Adjust the appearance and plating
- **Decision**: Is the appearance now satisfactory?
- **Success Path**: End
- **Failure Path**: End

### Start Over
- **Description**: Discard current attempt and restart process
- **Decision**: Decision to restart confirmed?
- **Success Path**: Gather Ingredients
- **Failure Path**: End

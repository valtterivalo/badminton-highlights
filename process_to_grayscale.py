import cv2

# Load your original screenshot
original_image = cv2.imread("templates/gameplay_template_original.jpg")

# Convert to grayscale
gray_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)

# Save the grayscale version
cv2.imwrite("templates/gameplay_template_gray.jpg", gray_image)

print("Grayscale template saved as 'templates/gameplay_template_gray.jpg'")
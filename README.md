# Project Title

A Flask-based web application designed for managing car sales. The application provides features such as user authentication, car listings, contact forms, and an admin dashboard.

## Features

- **User Authentication**: Registration and login functionality.
- **Car Listings**: Users can view cars for sale and their details.
- **Admin Dashboard**: Admins can manage car listings and users.
- **Responsive Design**: Front-end designed with HTML and JavaScript.
- **Contact Form**: Users can reach out for inquiries.

## Project Structure

```
Proiect_TW/
├── app.py                     # Main application file
├── app.db                     # SQLite database
├── templates/                 # HTML templates
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── cars_for_sale.html
│   ├── car_listing.html
│   ├── car_details.html
│   ├── admin_dashboard.html
│   └── contact_form.html
├── static/
│   ├── js/
│   │   └── timer.js           # JavaScript file for front-end logic
│   ├── assets/
│       └── images/            # Images used in the project
│           ├── day-exterior-4.png
│           ├── images.jpeg
│           ├── car_listing_bg.jpg
│           └── headerimage.jpg
└── .git/                      # Version control files
```

## Prerequisites

- Python 3.10 or higher
- Flask
- SQLite

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/ThisPDF/CarAuction.git
   ```

2. Navigate to the project directory:
   ```bash
   cd CARAUCTION
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python app.py
   ```

5. Access the application in your browser at `http://127.0.0.1:5000`.

## Usage

- **Home Page**: Browse the latest car listings.
- **Authentication**: Register or log in to access more features.
- **Admin Panel**: Manage users and listings (admin only).

## Contributing

1. Fork the repository.
2. Create a new branch for your feature:
   ```bash
   git checkout -b feature-name
   ```
3. Commit your changes:
   ```bash
   git commit -m "Description of changes"
   ```
4. Push to the branch:
   ```bash
   git push origin feature-name
   ```
5. Open a pull request.

## License

This project is licensed under the MIT License.



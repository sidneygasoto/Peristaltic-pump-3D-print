/////////////////////////////////////////////////////////////////////////////////////////////////////
// BMP280_DEV - I2C Communications (Alternative Address), Default Configuration, Normal Conversion
/////////////////////////////////////////////////////////////////////////////////////////////////////

#include < .h> // Include the BMP280_DEV.h library

float firstP, temperature, pressure, altitude; // Create the temperature, pressure and altitude variables
BMP280_DEV bmp280;                             // Instantiate (create) a BMP280_DEV object and set-up for I2C operation

void setup()
{
  Serial.begin(115200); // Initialise the serial port
  Serial.println("Modulo BMP280");
  bmp280.begin(BMP280_I2C_ALT_ADDR);           // Default initialisation with alternative I2C address (0x76), place the BMP280 into SLEEP_MODE
  bmp280.setPresOversampling(OVERSAMPLING_X4); // Set the pressure oversampling to X4
  //bmp280.setTempOversampling(OVERSAMPLING_X1);    // Set the temperature oversampling to X1
  bmp280.setIIRFilter(IIR_FILTER_4); // Set the IIR filter to setting 4
  //bmp280.setTimeStandby(TIME_STANDBY_250MS);     // Set the standby time to 2 seconds
  bmp280.startNormalConversion(); // Start BMP280 continuous conversion in NORMAL_MODE
  bmp280.getMeasurements(pressure);
  firstP = pressure;
}

void loop()
{
  if (bmp280.getMeasurements(temperature, pressure, altitude)) // Check if the measurement is complete
  {
    //Serial.print(temperature);                    // Display the results
    //Serial.print(F("*C   "));
    Serial.println(pressure - firstP);
    //Serial.print(F("hPa   "));
    //Serial.print(altitude);
    //Serial.println(F("m"));
  }
}

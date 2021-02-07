<img width="200" alt="portfolio_view" src="https://iriusrisk.com/wp-content/uploads/2020/10/logo-iriusrisk.svg">
# irius-cli - Command Line Interface for the IriusRisk threat modeling platform

This CLI utility calls the IriusRisk API to perform key operations on your threat model.  It's available as a single JAR and a compiled Linux binary.
## Usage
```bash
irius [-hV] [COMMAND]
  -h, --help      Show this help message and exit.
  -V, --version   Print version information and exit.
Commands:
  help            Displays help information about the specified command
  product         Display product related information
  threat          Display threats for a given product
  countermeasure  Display countermeasure information
  configure       Manage configuration
```
## Getting Started
1. Download the Linux binary from the releases or download the single JAR file from the releases and run it with a Java 11 JRE.
2. Set the URL of your IriusRisk instance:
```bash
./irius configure url set "https://myserver.iriusrisk.com/api/v1"
```
3. Set the API authentication token for your user to access the IriusRisk API:
```bash
./irius configure token set "my-unique-authentication-token"
```
These settings are stored in the file ~/.irius/credentials
## Building
### The JAR file
This project depends on the IriusRisk Java client library: https://github.com/iriusrisk/iriusrisk-client-lib/tree/develop which is not published to Maven central.
Download that library and install to your local maven repository.  The current version of this CLI depends on the develop branch of the client library. Once the library is installed in maven, then build the CLI:

```bash
mvn package
```
### The Native binary
This requires GraalVM for at least Java 11.
```bash
mvn package
```
### Modifying
There are a number of additional files needed by the GraalVM compiler to generate the native image, these are located in:
 src/main/resources/META-INF/native-image/com.iriusrisk.cli/irius-cli/

The native-image.properties file passes additional arguments to the native-image GraalVM command to locate these files.  If you add new commands to the CLI then you will need to regenerate these files using the agent provided by GraalVM: 
```bash
java -agentlib:native-image-agent=config-output-dir=src/main/resources/META-INF/native-image/com.iriusrisk.cli/irius-cli/
```
Note that an additional file from the iriusrisk-client-lib is also used to generate the binary, but that file is automatically generated when building that library.




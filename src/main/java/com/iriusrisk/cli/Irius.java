package com.iriusrisk.cli;

import com.iriusrisk.api.ProductsApi;
import com.iriusrisk.cli.commands.configure.Credentials;
import com.squareup.okhttp.OkHttpClient;
import com.iriusrisk.cli.commands.configure.ConfigureCommand;
import com.iriusrisk.cli.commands.configure.CredentialUtils;
import com.iriusrisk.cli.commands.countermeasure.CountermeasureCommand;
import com.iriusrisk.cli.commands.product.ProductCommand;
import com.iriusrisk.cli.commands.threat.ThreatCommand;
import picocli.CommandLine;

import java.io.File;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Proxy;

@CommandLine.Command(name = "Irius CLI", version = "Irius CLI v1.0", mixinStandardHelpOptions = true, subcommands = {
        CommandLine.HelpCommand.class, ProductCommand.class, ThreatCommand.class, CountermeasureCommand.class,
        ConfigureCommand.class
})
public class Irius implements Runnable {

    /**
     * The home directory Irius folder.
     */
    private static final String IRIUS_PATH = System.getProperty("user.home") + File.separator + ".irius";

    /**
     * The name of the credentials file, located at {@link #IRIUS_PATH}.
     */
    private static final String CREDENTIALS_FILE = "credentials";

    /**
     * The API url.
     */
    private static final String API_URL = "https://demo.iriusrisk.com/api/v1";

    /**
     * The API handler.
     */
    private static final ProductsApi API = new ProductsApi();

    /**
     * The API token.
     */
    private static String apiToken;

    /**
     * Command line Spec for handling missing subcommands.
     */
    @CommandLine.Spec private CommandLine.Model.CommandSpec spec;

    /**
     * Constructor.
     */
    public Irius() {
        initialize();
    }

    /**
     * Performs API initialization.
     */
    private void initialize() {
        OkHttpClient httpClient = new OkHttpClient();
        String proxyHost = System.getProperty("proxy.host");

        if (proxyHost != null) {
            int proxyPort = Integer.parseInt(System.getProperty("proxy.port"));
            Proxy proxy = new Proxy(Proxy.Type.HTTP, new InetSocketAddress(proxyHost, proxyPort));
            httpClient.setProxy(proxy);
        }

        API.getApiClient().setBasePath(API_URL);
        API.getApiClient().setHttpClient(httpClient);
        API.getApiClient().setVerifyingSsl(false);

        Credentials c = CredentialUtils.readCredentials();
        if (c != null) {
            apiToken = c.getApiToken();
        }
    }

    @Override
    public void run() {
        throw new CommandLine.ParameterException(spec.commandLine(), "Missing required subcommand");
    }

    /**
     * Returns the API handler.
     *
     * @return the API handler
     */
    public static ProductsApi getApi() {
        return API;
    }

    /**
     * Returns the API token.
     *
     * @return the Products API object
     */
    public static String getApiToken() {
        return apiToken;
    }

    /**
     * Sets the API token.
     *
     * @param apiToken the API token
     */
    public static void setApiToken(String apiToken) {
        Irius.apiToken = apiToken;
    }

    /**
     * Returns the path of the Irius configuration directory.
     *
     * @return Irius configuration path
     */
    public static String getIriusPath() {
        return IRIUS_PATH;
    }

    /**
     * Returns the name of the credentials file.
     *
     * @return the credentials file
     */
    public static String getCredentialsFile() {
        return CREDENTIALS_FILE;
    }

    /**
     * Main method.
     *
     * @param args not used
     */
    public static void main(String[] args) {
        CommandLine commandLine = new CommandLine(new Irius());
        System.exit(commandLine.execute(args));
    }
}



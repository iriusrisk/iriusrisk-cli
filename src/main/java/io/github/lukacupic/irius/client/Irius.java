package io.github.lukacupic.irius.client;

import com.iriusrisk.api.ProductsApi;
import com.squareup.okhttp.OkHttpClient;
import io.github.lukacupic.irius.client.commands.ErrorUtil;
import io.github.lukacupic.irius.client.commands.configure.ConfigureCommand;
import io.github.lukacupic.irius.client.commands.configure.CredentialsUtil;
import io.github.lukacupic.irius.client.commands.countermeasure.CountermeasureCommand;
import io.github.lukacupic.irius.client.commands.product.ProductCommand;
import io.github.lukacupic.irius.client.commands.threat.ThreatCommand;
import picocli.CommandLine;

import java.io.File;
import java.net.InetSocketAddress;
import java.net.Proxy;

@CommandLine.Command(name = "Irius CLI", version = "Irius CLI v1.0", mixinStandardHelpOptions = true, subcommands = {
        CommandLine.HelpCommand.class, ProductCommand.class, ThreatCommand.class, CountermeasureCommand.class,
        ConfigureCommand.class
})
public class Irius implements Runnable {

    /**
     * The single instance of the Irius main program/command.
     */
    private static Irius instance;

    /**
     * The home directory Irius folder.
     */
    private static final String IRIUS_PATH = System.getProperty("user.home") + File.separator + ".irius";

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
        Irius.instance = this;
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

        apiToken = CredentialsUtil.readCredential("token");
    }

    @Override
    public void run() {
        throw new CommandLine.ParameterException(spec.commandLine(), "Missing required subcommand");
    }

    /**
     * Gets the Irius instance.
     *
     * @return the Irius instance
     */
    public static Irius getInstance() {
        return instance;
    }

    /**
     * Returns the API handler.
     *
     * @return the API handler
     */
    public ProductsApi getApi() {
        return API;
    }

    /**
     * Returns the API token.
     *
     * @return the Products API object
     */
    public String getApiToken() {
        return apiToken;
    }

    /**
     * Sets the API token.
     *
     * @param apiToken the API token
     */
    public void setApiToken(String apiToken) {
        Irius.apiToken = apiToken;
    }

    /**
     * Returns the path of the Irius configuration directory.
     *
     * @return Irius configuration path
     */
    public String getIriusPath() {
        return IRIUS_PATH;
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



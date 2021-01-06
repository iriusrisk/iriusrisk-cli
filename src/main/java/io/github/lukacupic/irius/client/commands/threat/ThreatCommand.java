package io.github.lukacupic.irius.client.commands.threat;

import com.iriusrisk.ApiException;
import com.iriusrisk.api.ProductsApi;
import com.iriusrisk.model.ComponentUseCaseThreatShort;
import io.github.lukacupic.irius.client.Irius;
import io.github.lukacupic.irius.client.commands.ErrorUtil;
import picocli.CommandLine;

import java.util.List;

@CommandLine.Command(name = "threat", description = "Display threat information")
public class ThreatCommand implements Runnable {

    /**
     * Command line Spec for handling missing subcommands.
     */
    @CommandLine.Spec private CommandLine.Model.CommandSpec spec;

    /**
     * The Products API.
     */
    private ProductsApi api;

    /**
     * The API token.
     */
    private String token;

    /**
     * Constructor.
     */
    public ThreatCommand() {
        this.api = Irius.getInstance().getApi();
        this.token = Irius.getInstance().getApiToken();
    }

    @CommandLine.Command(name = "list", description = "List all threats for a given product")
    void listCommand(@CommandLine.Parameters(paramLabel = "id", description = "Product ID") String id) {
        try {
            List<ComponentUseCaseThreatShort> threats = api.productsRefThreatsGet(token, id);
            System.out.println(threats);

        } catch (ApiException e) {
            ErrorUtil.apiError(spec);
        }
    }

    @Override
    public void run() {
        ErrorUtil.subcommandError(spec);
    }
}
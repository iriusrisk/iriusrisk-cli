package com.iriusrisk.cli.commands.threat;


import com.iriusrisk.api.client.ProductsApi;
import com.iriusrisk.api.client.model.ComponentUseCaseThreatShort;
import com.iriusrisk.cli.Irius;
import com.iriusrisk.cli.commands.ErrorUtil;
import com.iriusrisk.cli.commands.configure.CredentialUtils;
import org.springframework.web.client.RestClientException;
import picocli.CommandLine;

import java.util.List;

@CommandLine.Command(name = "threat", description = "Display threats for a given product")
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
        this.api = Irius.getApi();
        this.token = Irius.getApiToken();
    }

    @CommandLine.Command(name = "list", description = "List all threats for a given product")
    void listCommand(@CommandLine.Parameters(paramLabel = "id", description = "Product ID") String id) {
        CredentialUtils.checkToken(spec);
        try {
            List<ComponentUseCaseThreatShort> threats = api.productsRefThreatsGet(token, id);
            System.out.println(threats);

        } catch (RestClientException e) {
            ErrorUtil.apiError(spec, e.getMessage());

        }
        System.out.println("done");

    }

    @Override
    public void run() {
        ErrorUtil.subcommandError(spec);
    }
}
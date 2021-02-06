package com.iriusrisk.cli.commands.countermeasure;


import com.iriusrisk.api.client.ProductsApi;
import com.iriusrisk.api.client.model.ComponentControl;
import com.iriusrisk.cli.Irius;
import com.iriusrisk.cli.commands.ErrorUtil;
import com.iriusrisk.cli.commands.configure.CredentialUtils;
import org.springframework.web.client.RestClientException;
import picocli.CommandLine;

import java.util.List;

@CommandLine.Command(name = "countermeasure", description = "Display countermeasure information")
public class CountermeasureCommand implements Runnable {

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
    public CountermeasureCommand() {
        this.api = Irius.getApi();
        this.token = Irius.getApiToken();
    }

    @CommandLine.Parameters(paramLabel = "<product unique ID>", description = "Product ID")
    private String id;

    @CommandLine.Option(names = {"--required"}, description = "Only display required countermeasures")
    boolean required;

    @CommandLine.Option(names = {"--implemented"}, description = "Only display Implemented countermeasures")
    boolean implemented;

    @Override
    public void run() {
        CredentialUtils.checkToken(spec);

        try {
            List<ComponentControl> countermeasures;
            if (required) {
                countermeasures = api.productsRefControlsRequiredGet(token, id);

            } else if (implemented) {
                countermeasures = api.productsRefControlsImplementedGet(token, id);

            } else {
                countermeasures = api.productsRefControlsGet(token, id);
            }

            System.out.println(countermeasures);

        } catch (RestClientException e) {
            ErrorUtil.apiError(spec, e.getMessage());
        }
    }
}
package com.iriusrisk.cli.commands.countermeasure;

import com.iriusrisk.ApiException;
import com.iriusrisk.api.ProductsApi;
import com.iriusrisk.cli.Irius;
import com.iriusrisk.cli.commands.ErrorUtil;
import com.iriusrisk.cli.commands.configure.CredentialUtils;
import com.iriusrisk.model.ComponentControl;
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

    @CommandLine.Option(names = {"--required"}, description = "Required countermeasure")
    boolean required;

    @CommandLine.Option(names = {"--implemented"}, description = "Implemented countermeasure")
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

        } catch (ApiException e) {
            ErrorUtil.apiError(spec, e.getMessage());
        }
    }
}
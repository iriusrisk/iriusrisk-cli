package com.iriusrisk.cli.commands.product;

import com.iriusrisk.ApiException;
import com.iriusrisk.api.ProductsApi;
import com.iriusrisk.cli.Irius;
import com.iriusrisk.cli.commands.configure.CredentialUtils;
import com.iriusrisk.model.Product;
import com.iriusrisk.model.ProductShort;
import com.iriusrisk.cli.commands.ErrorUtil;
import picocli.CommandLine;

import java.util.List;

@CommandLine.Command(name = "product", description = "Display product-related information")
public class ProductCommand implements Runnable{

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
    public ProductCommand() {
        this.api = Irius.getApi();
        this.token = Irius.getApiToken();
    }


    @CommandLine.Command(name = "list", description = "List all products")
    void listCommand() {
        CredentialUtils.checkToken(spec);

        try {
            List<ProductShort> products = api.productsGet(token, null, null, null);
            products.forEach(System.out::println);

        } catch (ApiException e) {
            ErrorUtil.apiError(spec, e.getMessage());
        }
    }

    @CommandLine.Command(name = "show", description = "Display product details")
    void showCommand(@CommandLine.Parameters(paramLabel = "<product unique ID>", description = "Product ID") String id) {
        CredentialUtils.checkToken(spec);

        try {
            Product product = api.productsRefGet(token, id);
            System.out.println(product);

        } catch (ApiException e) {
            ErrorUtil.apiError(spec, e.getMessage());
        }
    }

    @Override
    public void run() {
        ErrorUtil.subcommandError(spec);
    }
}